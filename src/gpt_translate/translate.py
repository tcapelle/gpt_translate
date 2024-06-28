import yaml
import json
import logging
import asyncio
from typing import Optional
from pathlib import Path
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,  # for exponential backoff
)

import weave
from pydantic import model_validator, Field

from gpt_translate.prompts import PromptTemplate
from gpt_translate.loader import remove_markdown_comments, MDPage, split_markdown
from gpt_translate.utils import file_is_empty, count_tokens
from gpt_translate.validate import validate_links, validate_headers


# Use the OpenAI API in async mode
client = AsyncOpenAI()

## Globals
REPLACE = False
REMOVE_COMMENTS = True
MAX_OPENAI_CONCURRENT_CALLS = 7  # Adjust the limit as needed
MAX_CHUNK_TOKENS = 3600


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def completion_with_backoff(**kwargs):
    return await client.chat.completions.create(**kwargs)


@weave.op
async def translate_content(md_content: str, prompt: PromptTemplate, **model_args):
    """Translate a markdown chunk asynchronously
    md_content: markdown content
    prompt: PromptTemplate object
    return: translated page
    """
    res = await completion_with_backoff(
        messages=prompt.format(md_chunk=md_content), **model_args
    )
    output = res.choices[0].message.content
    logging.debug(
        f"[blue]OpenAI response:\n{output[:100]}...[/blue]", extra={"markup": True}
    )
    logging.debug(res.usage)
    return output


class Translator(weave.Object):
    "A class to translate markdown files asynchronously"
    config_folder: Path
    language: str = "ja"
    do_evaluation: bool = True
    model_args: dict = dict(model="gpt-4o", temperature=1.0)
    max_chunk_tokens: int = MAX_CHUNK_TOKENS
    evaluation_prompt: Optional[str] = Field(default=None)
    prompt_template: PromptTemplate = Field(default=None)

    @model_validator(mode="before")
    def initialize_fields(cls, values):
        config_folder = Path(values.get("config_folder"))
        language = values.get("language", "ja")
        prompt_template = PromptTemplate.from_files(
            config_folder / "system_prompt.txt",
            config_folder / "human_prompt.txt",
            config_folder / f"language_dicts/{language}.yaml",
        )
        if (config_folder / "evaluation_prompt.txt").exists():
            evaluation_prompt = (config_folder / "evaluation_prompt.txt").read_text()
        else:
            evaluation_prompt = None

        values.update(
            {
                "config_folder": config_folder,
                "prompt_template": prompt_template,
                "evaluation_prompt": evaluation_prompt,
            }
        )
        return values

    @weave.op
    async def translate_splitted_md(
        self,
        splitted_markdown: list[str],
        sep: str = "\n\n",
    ) -> str:
        """Translate a list of markdown chunks asynchronously
        splitted_markdown: list of markdown chunks
        prompt: PromptTemplate object
        max_chunk_tokens: maximum number of tokens per chunk
        sep: separator between chunks
        model_args: arguments to pass to the completion_with_backoff function
        return: translated markdown file
        """

        tasks = []
        packed_chunks = ""
        packed_chunks_len = 0

        translated_chunks = []
        for i, chunk in enumerate(splitted_markdown):
            n_tokens = count_tokens(chunk)

            if packed_chunks_len + n_tokens <= self.max_chunk_tokens:
                logging.debug(f"Packing chunk {i} with {n_tokens} tokens")
                packed_chunks += sep + chunk
                packed_chunks_len += n_tokens
            else:
                logging.debug(f">> Translating {packed_chunks_len} tokens")
                translated_chunk = await translate_content(
                    packed_chunks, self.prompt_template, **self.model_args
                )
                translated_chunks.append(translated_chunk)
                packed_chunks = chunk
                packed_chunks_len = n_tokens

        if packed_chunks:
            logging.debug(f">> Translating {packed_chunks_len} tokens (last chunk)")
            translated_chunk = await translate_content(
                packed_chunks, self.prompt_template, **self.model_args
            )
            translated_chunks.append(translated_chunk)
        return sep.join(translated_chunks)

    @weave.op
    async def translate_file(self, md_file: str, remove_comments: bool = True):
        """Translate a markdown file asynchronously"""
        with open(md_file, "r") as f:
            md_content = f.read()
        if remove_comments:
            logging.debug("Removing comments")
            md_content = remove_markdown_comments(md_content)
        if len(md_content.strip()) < 20:
            logging.warning(f"File may be empty: {md_file}")
        md_page = MDPage(filename=md_file, raw_content=md_content)
        logging.debug(
            f"[bold red blink]Calling OpenAI [/bold red blink]with {self.model_args}\nFile: {md_file}\nContent: {md_content[:100]}...",
            extra={"markup": True},
        )
        translated_page = await self.translate_page(md_page)

        if md_page.header.description:
            logging.debug(
                f"Translating header description: {md_page.header.description}"
            )
            translated_page.header.description = (
                await self.translate_header_description(md_page)
            )

        if self.evaluate:
            evaluation_results = await self.evaluate(md_page, translated_page)
            return {
                "translated_page": translated_page,
                "evaluation_results": evaluation_results,
            }
        return {"translated_page": translated_page}

    @weave.op
    async def translate_page(self, md_page: MDPage):
        """Translate a markdown page asynchronously"""
        chunks = split_markdown(md_page.content)
        translated_content = await self.translate_splitted_md(chunks)

        return md_page.from_translated(translated_content, fix_links=False)

    @weave.op
    async def translate_header_description(self, md_page: MDPage):
        """Translate the header description"""
        return await translate_content(
            md_page.header.description, self.prompt_template, **self.model_args
        )

    @weave.op
    async def evaluate(self, md_page: MDPage, translated_page: MDPage):
        """Validate the translation"""
        links_validation = validate_links(md_page, translated_page)
        headers_validation = validate_headers(md_page, translated_page)
        logging.debug(f"✅ Links validation: {links_validation}")
        logging.debug(f"✅ Headers validation: {headers_validation}")
        translation_validation = await self.evaluate_translation(
            md_page, translated_page
        )
        logging.debug(f"✅ Translation validation: {translation_validation}")
        return {
            "links_validation": links_validation,
            "headers_validation": headers_validation,
            "translation_validation": translation_validation,
        }

    @weave.op
    async def evaluate_translation(self, md_page: MDPage, translated_page: MDPage):
        """Evaluate the translation"""
        messages = self.prompt_template.format(md_chunk=md_page.content)
        messages.append({"role": "assistant", "content": f"{translated_page.content}"})
        messages.append({"role": "user", "content": self.evaluation_prompt})
        res = await completion_with_backoff(
            messages=messages,
            **self.model_args,
            response_format={"type": "json_object"},
        )
        extracted = res.choices[0].message.content
        analysis = json.loads(extracted)
        return analysis


@weave.op
async def _translate_file(
    input_file: str,  # File to translate
    out_file: str,  # File to save the translated file to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
    do_evaluation: bool = True,  # Evaluate the translated file
    model_args: dict = dict(model="gpt-4o", temperature=1.0),  # model args
    max_chunk_tokens: int = MAX_CHUNK_TOKENS,  # max number of tokens in a chunk
) -> MDPage:
    """Translate a markdown file asynchronously"""
    if file_is_empty(input_file):
        raise ValueError(f"File {input_file} is empty")

    # check it is a md file
    if Path(input_file).suffix != ".md":
        raise ValueError(f"File {input_file} is not a markdown file")
    out_file = Path(out_file)
    if out_file.exists() and not replace and not file_is_empty(out_file):
        logging.info(f"File {out_file} already exists. Use --replace to overwrite.")
    else:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            translator = Translator(
                config_folder=config_folder,
                language=language,
                do_evaluation=do_evaluation,
                model_args=model_args,
                max_chunk_tokens=max_chunk_tokens,
            )
            translation_results = await translator.translate_file(
                input_file, remove_comments
            )
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(str(translation_results["translated_page"]))
            logging.info(
                f"✅ Translated file saved to [green]{out_file}[/green]",
                extra={"markup": True},
            )
            return translation_results
        except Exception as e:
            logging.error(f"❌ Error translating {input_file}: {e}")
            # raise e


@weave.op
async def _translate_files(
    input_files: list[str],  # Files to translate
    input_folder: str,  # folder where the file lives
    out_folder: str,  # Folder to save the translated files to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
    do_evaluation: bool = True,  # Evaluate the translated file
    model_args: dict = dict(model="gpt-4o", temperature=1.0),  # model args
    max_openai_concurrent_calls: int = MAX_OPENAI_CONCURRENT_CALLS,  # Maximum number of concurrent calls to OpenAI
    max_chunk_tokens: int = MAX_CHUNK_TOKENS,  # max number of tokens in a chunk
):
    # let's make input_files support a txt file with a list of files
    if Path(input_files).suffix == ".txt":
        logging.info(f"Reading {input_files}")
        input_files = Path(input_files).read_text().splitlines()
    input_files = [Path(f) for f in input_files if Path(f).suffix == ".md"]
    logging.info(f"Translating {len(input_files)} files")
    input_files.sort()
    input_folder = Path(input_folder)
    out_folder = Path(out_folder)
    if not input_folder.is_dir():
        raise ValueError(f"{input_folder} is not a folder")

    semaphore = asyncio.Semaphore(max_openai_concurrent_calls)

    async def _translate_with_semaphore(md_file):
        async with semaphore:
            out_file = out_folder / md_file.relative_to(input_folder)
            return await _translate_file(
                input_file=str(md_file),
                out_file=str(out_file),
                replace=replace,
                language=language,
                config_folder=config_folder,
                remove_comments=remove_comments,
                do_evaluation=do_evaluation,
                model_args=model_args,
                max_chunk_tokens=max_chunk_tokens,
            )

    tasks = [_translate_with_semaphore(md_file) for md_file in input_files]

    await tqdm.gather(*tasks, desc="Translating files")
