import yaml
import json
import logging
from rich.logging import RichHandler
from pathlib import Path
import aiohttp
import asyncio
from tqdm.asyncio import tqdm
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,  # for exponential backoff
)
from fastcore.script import call_parse, Param, store_true, store_false

import weave
from pydantic import model_validator, Field

from gpt_translate.prompts import PromptTemplate
from gpt_translate.loader import remove_markdown_comments, split_markdown, MDPage
from gpt_translate.utils import count_tokens, get_md_files, file_is_empty
from gpt_translate.validate import validate_links, validate_headers


def setup_logging(debug=False, silence_openai=True, weave_project=None):
    """Setup logging"""
    # Setup rich logger
    level = "DEBUG" if debug else "INFO"
    logging.basicConfig(
        level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )

    # silence openai logger
    if silence_openai:
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
    if weave_project:
        weave.init(weave_project)

# Use the OpenAI API in async mode
client = AsyncOpenAI()

## Global
REPLACE = False
REMOVE_COMMENTS = True
MAX_OPENAI_CONCURRENT_CALLS = 7  # Adjust the limit as needed
DEBUG = False
semaphore = asyncio.Semaphore(MAX_OPENAI_CONCURRENT_CALLS)


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
    validate: bool = True
    validation_prompt: str = Field(default=None)
    prompt_template: PromptTemplate = Field(default=None)
    model_args: dict = Field(default=None)

    @model_validator(mode="before")
    def initialize_fields(cls, values):
        config_folder = Path(values.get("config_folder"))
        language = values.get("language", "ja")
        prompt_template = PromptTemplate.from_files(
            config_folder / "system_prompt.txt",
            config_folder / "human_prompt.txt",
            config_folder / f"language_dicts/{language}.yaml",
        )
        if (config_folder / "validation_prompt.txt").exists():
            validation_prompt = (config_folder / "validation_prompt.txt").read_text()
        else:
            validation_prompt = None
        with open(config_folder / "model_config.yaml", "r") as file:
            model_args = yaml.safe_load(file)
            logging.debug(f"Model args: {model_args}")

        values.update(
            {
                "config_folder": config_folder,
                "prompt_template": prompt_template,
                "validation_prompt": validation_prompt,
                "model_args": model_args,
            }
        )
        return values

    @weave.op
    async def translate_file(self, md_file: str, remove_comments: bool = True):
        """Translate a markdown file asynchronously"""
        with open(md_file, "r") as f:
            md_content = f.read()
        if remove_comments:
            logging.debug("Removing comments")
            md_content = remove_markdown_comments(md_content)
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
            translated_page.header.description = await self.translate_header_description(md_page)
            
        if self.validate:
            validation_results = await self.validation(md_page, translated_page)
            return {"translated_page": translated_page, "validation_results": validation_results}
        return {"translated_page": translated_page}
    
    @weave.op
    async def translate_page(self, md_page: MDPage):
        """Translate a markdown page asynchronously"""
        translated_content = await translate_content(
            md_page.content,
            self.prompt_template,
            **self.model_args,
        )
        return md_page.from_translated(translated_content, fix_links=False)

    @weave.op
    async def translate_header_description(self, md_page: MDPage):
        """Translate the header description"""
        return await translate_content(
            md_page.header.description, self.prompt_template, **self.model_args
        )

    @weave.op
    async def validation(self, md_page: MDPage, translated_page: MDPage):
        """Validate the translation"""
        links_validation = validate_links(md_page, translated_page)
        headers_validation = validate_headers(md_page, translated_page)
        logging.debug(f"✅ Links validation: {links_validation}")
        logging.debug(f"✅ Headers validation: {headers_validation}")
        translation_validation = await self.validate_translation(
            md_page, translated_page
        )
        logging.debug(f"✅ Translation validation: {translation_validation}")
        return {
            "links_validation": links_validation,
            "headers_validation": headers_validation,
            "translation_validation": translation_validation,
        }

    @weave.op
    async def validate_translation(self, md_page: MDPage, translated_page: MDPage):
        """Validate the translation"""
        messages = self.prompt_template.format(md_chunk=md_page.content)
        messages.append({"role": "assistant", "content": f"{translated_page.content}"})
        messages.append({"role": "user", "content": self.validation_prompt})
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
    validate: bool = True,  # Validate the translated file
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
                config_folder=config_folder, language=language, validate=validate
            )
            async with semaphore:
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
            raise e
            logging.error(f"Error translating {input_file}: {e}")


@weave.op
async def _translate_files(
    input_files: list[str],  # Files to translate
    input_folder: str,  # folder where the file lives
    out_folder: str,  # Folder to save the translated files to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
):
    input_files = [Path(f) for f in input_files if Path(f).suffix == ".md"]
    logging.info(
        f"Translating {len(input_files)} files\n"
        f"Max concurrent calls to OpenAI: {MAX_OPENAI_CONCURRENT_CALLS}\n"
        f"Removing comments: {remove_comments}\n"
        f"Replace existing files: {replace}\n"
        f"Language: {language}\n"
        f"Config folder: {config_folder}\n"
        f"Output folder: {out_folder}"
    )
    input_folder = Path(input_folder)
    out_folder = Path(out_folder)
    if not input_folder.is_dir():
        raise ValueError(f"{input_folder} is not a folder")

    tasks = []

    for md_file in input_files:
        out_file = out_folder / md_file.relative_to(input_folder)
        tasks.append(
            _translate_file(
                str(md_file),
                str(out_file),
                replace,
                language,
                config_folder,
                remove_comments,
            )
        )
    
    await tqdm.gather(*tasks, desc="Translating files")


# this function can be called using gpt_translate.file
@call_parse
def translate_file(
    input_file: Param("File to translate", str),
    out_file: Param("File to save the translated file to", str),
    replace: Param("Replace existing file", store_true) = REPLACE,
    language: Param("Language to translate to", str) = "es",
    config_folder: Param("Config folder", str) = "./configs",
    remove_comments: Param("Remove comments", store_false) = REMOVE_COMMENTS,
    debug: Param("Debug mode", store_true) = DEBUG,
    weave_project: Param("Weave project", str) = None,
):
    setup_logging(debug, weave_project=weave_project)
    asyncio.run(
        _translate_file(
            input_file,
            out_file,
            replace,
            language,
            config_folder,
            remove_comments,
        )
    )

# this function can be called using gpt_translate.files
@call_parse
def translate_files(
    input_files: Param("Files to translate", nargs="+"),
    input_folder: Param("Folder to translate", str) = "docs/",
    out_folder: Param("Folder to save the translated files to", str) = "translated/",
    replace: Param("Replace existing file", store_true) = REPLACE,
    language: Param("Language to translate to", str) = "es",
    config_folder: Param("Config folder", str) = "./configs",
    remove_comments: Param("Remove comments", store_false) = REMOVE_COMMENTS,
    debug: Param("Debug mode", store_true) = DEBUG,
    weave_project: Param("Weave project", str) = None,
):
    setup_logging(debug, weave_project=weave_project)
    asyncio.run(
        _translate_files(
            input_files,
            input_folder,
            out_folder,
            replace,
            language,
            config_folder,
            remove_comments,
        )
    )

# this function can be called using gpt_translate.folder
@call_parse
def translate_folder(
    input_folder: Param("Folder to translate", str),
    out_folder: Param("Folder to save the translated files to", str) = "translated/",
    replace: Param("Replace existing files", store_true) = REPLACE,
    language: Param("Language to translate to", str) = "es",
    config_folder: Param("Config folder", str) = "./configs",
    remove_comments: Param("Remove comments", store_false) = REMOVE_COMMENTS,
    limit: Param("Limit number of files to translate", int) = None,
    debug: Param("Debug mode", store_true) = DEBUG,
    weave_project: Param("Weave project", str) = None,
):
    """Translate all markdown files in a folder respecting the folder hierarchy"""
    setup_logging(debug, weave_project=weave_project)
    input_files = get_md_files(input_folder)[:limit]
    asyncio.run(
        _translate_files(
            input_files,
            input_folder,
            out_folder,
            replace,
            language,
            config_folder,
            remove_comments,
        )
    )
