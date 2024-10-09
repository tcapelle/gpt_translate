import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass
from tqdm.asyncio import tqdm

import weave
from pydantic import model_validator, Field

from gpt_translate.prompts import PromptTemplate
from gpt_translate.loader import (
    remove_markdown_comments,
    MDPage,
    Header,
)
from gpt_translate.utils import (
    file_is_empty,
    count_tokens,
    longer_create,
    to_weave_dataset,
)


## Globals
REPLACE = False
REMOVE_COMMENTS = True
MAX_OPENAI_CONCURRENT_CALLS = 7  # Adjust the limit as needed


@dataclass
class TranslationResult:
    content: str
    tokens: int


@weave.op
async def translate_content(md_content: str, prompt: PromptTemplate, **model_args):
    """Translate a markdown chunk asynchronously
    md_content: markdown content
    prompt: PromptTemplate object
    return: translated page
    """
    output = await longer_create(
        messages=prompt.format(md_chunk=md_content), **model_args
    )
    return TranslationResult(content=output, tokens=count_tokens(output))


class Translator(weave.Object):
    "A class to translate markdown files asynchronously"
    config_folder: Path
    language: str = "ja"
    do_translate_header_description: bool = True
    model_args: dict = dict(model="gpt-4o", temperature=1.0)
    prompt_template: PromptTemplate = Field(default=None)

    @model_validator(mode="before")
    def initialize_fields(cls, values):
        config_folder = Path(values.get("config_folder"))
        language = values.get("language", "ja")
        prompt_template = PromptTemplate.from_folder(config_folder, language)
        values.update(
            {
                "config_folder": config_folder,
                "prompt_template": prompt_template,
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
        if len(md_content.strip()) < 20:
            logging.warning(f"File may be empty: {md_file}")
        md_page = MDPage.from_raw_content(filename=md_file, raw_content=md_content)
        logging.debug(
            f"[bold red blink]Calling OpenAI [/bold red blink]with {self.model_args}\nFile: {md_file}\nContent:\n{md_content[:100]}...",
            extra={"markup": True},
        )
        translated_page = await self.translate_page(md_page)
        return {"original_page": md_page, "translated_page": translated_page}

    @weave.op
    async def translate_page(self, md_page: MDPage, translate_header: bool = True):
        """Translate a markdown page asynchronously"""
        # chunks = split_markdown(md_page.content)
        # translated_content = await self.translate_splitted_md(chunks)
        translated_content = await translate_content(
            md_page.content, self.prompt_template, **self.model_args
        )
        logging.debug(f"Translated content: {translated_content}")
        if (
            md_page.header.description and self.do_translate_header_description
        ):  # check if header contains a description
            translated_header_description = await self.translate_header_description(
                md_page
            )
            logging.debug(
                f"Translating header description: {md_page.header.description}"
            )
            new_header = Header(
                title=md_page.header.title,
                description=(
                    translated_header_description.content
                    if md_page.header.description
                    else None
                ),
                slug=md_page.header.slug,
                displayed_sidebar=md_page.header.displayed_sidebar,
                imports=md_page.header.imports,
            )
        else:
            new_header = md_page.header
        return MDPage(
            filename=md_page.filename,
            content=translated_content.content,
            header=new_header,
        )

    @weave.op
    async def translate_header_description(self, md_page: MDPage):
        """Translate the header description"""
        translated_description = await translate_content(
            md_page.header.description, self.prompt_template, **self.model_args
        )
        return translated_description


@weave.op
async def _translate_file(
    input_file: str,  # File to translate
    out_file: str,  # File to save the translated file to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
    do_translate_header_description: bool = True,  # Translate the header description
    model_args: dict = dict(model="gpt-4o", temperature=1.0),  # model args
) -> MDPage:
    """Translate a markdown file asynchronously"""
    if file_is_empty(input_file):
        raise ValueError(f"File {input_file} is empty")

    # check it is a md file
    if Path(input_file).suffix not in [".md", ".mdx"]:
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
                do_translate_header_description=do_translate_header_description,
                model_args=model_args,
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
            raise e


@weave.op
async def _translate_files(
    input_files: list[str],  # Files to translate
    input_folder: str,  # folder where the file lives
    out_folder: str,  # Folder to save the translated files to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
    do_translate_header_description: bool = True,  # Translate the header description
    model_args: dict = dict(model="gpt-4o", temperature=1.0),  # model args
    max_openai_concurrent_calls: int = MAX_OPENAI_CONCURRENT_CALLS,  # Maximum number of concurrent calls to OpenAI
):
    # let's make input_files support a txt file with a list of files
    if not isinstance(input_files, list):
        if Path(input_files).suffix == ".txt":
            logging.info(f"Reading {input_files}")
        input_files = Path(input_files).read_text().splitlines()
    input_files = [
        Path(f)
        for f in input_files
        if (Path(f).suffix in [".md", ".mdx"] and Path(f).exists())
    ]
    logging.info(
        f"Translating {len(input_files)} file" + ("s" if len(input_files) > 1 else "")
    )
    input_files.sort()
    input_folder = Path(input_folder)
    out_folder = Path(out_folder)
    if not input_folder.is_dir():
        raise ValueError(f"{input_folder} is not a folder")

    semaphore = asyncio.Semaphore(max_openai_concurrent_calls)

    async def _translate_with_semaphore(md_file):
        async with semaphore:
            out_file = out_folder / md_file.relative_to(input_folder)
            translation_results = await _translate_file(
                input_file=str(md_file),
                out_file=str(out_file),
                replace=replace,
                language=language,
                config_folder=config_folder,
                remove_comments=remove_comments,
                do_translate_header_description=do_translate_header_description,
                model_args=model_args,
            )
            translation_results.update(
                {
                    "input_file": str(md_file),
                    "output_file": str(out_file),
                    "language": language,
                }
            )
            return translation_results

    tasks = [_translate_with_semaphore(md_file) for md_file in input_files]

    results = await tqdm.gather(*tasks, desc="Translating files")

    dataset = to_weave_dataset(name=f"Translation-{language}", rows=results)
    weave.publish(dataset)


if __name__ == "__main__":
    from gpt_translate.cli import setup_logging

    setup_logging(debug=True, silence_openai=True, weave_project="gpt-translate")
    asyncio.run(
        _translate_files(
            input_files="one.txt",
            input_folder="../docodile/docs_main/",
            out_folder="../docodile/docs/",
            replace=True,
            language="ja",
            config_folder="./configs",
        )
    )
