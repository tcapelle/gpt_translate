import asyncio
import time
from typing import Any
from pathlib import Path
from copy import copy
from dataclasses import dataclass
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
    gather_with_progress,
    console,
    logger,
)


## Globals
REPLACE = False
REMOVE_COMMENTS = True
MAX_CONCURRENT_CALLS = 7  # Adjust the limit as needed
MIN_CONTENT_LENGTH = 10

@dataclass
class TranslationResult:
    content: str
    tokens: int


@weave.op
async def translate_content(md_content: str, prompt: PromptTemplate, **model_args) -> TranslationResult:
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
    do_translate_header_title: bool = True
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
    async def translate_file(self, md_file: str, remove_comments: bool = True) -> dict[str, Any]:
        """Translate a markdown file asynchronously"""
        with open(md_file, "r") as f:
            raw_content = f.read()
        if remove_comments:
            logger.debug("Removing comments")
            raw_content_cleaned = remove_markdown_comments(raw_content)

        md_page = MDPage.from_raw_content(filename=md_file, raw_content=raw_content_cleaned)
        logger.debug(
            f"[bold red blink]Calling OpenAI [/bold red blink]with {self.model_args}\nFile: {md_file}\nContent:\n{md_page.content[:100]}...",
            extra={"markup": True},
        )
        translated_page = await self.translate_page(md_page)
        return {"original_page": md_page, "translated_page": translated_page, "error": None}

    @weave.op
    async def translate_page(self, md_page: MDPage, translate_header: bool = True):
        """Translate a markdown page asynchronously"""
        if len(md_page.content.strip()) < MIN_CONTENT_LENGTH:
            translated_content = md_page.content
            logger.warning(f"Skipping translation of {md_page} because it is empty")
        else:
            translated_content = await translate_content(
                md_page.content, self.prompt_template, **self.model_args
            )
            translated_content = str(translated_content.content)

        logger.debug(f"Translated content: {translated_content}")
        logger.debug(f"Header {md_page.header}")
        if md_page.header.description and self.do_translate_header_description:
            translated_header_description = await self.translate_header_item(
                md_page.header.description
            )
            
            # Ensure the translated description is a string
            translated_desc = str(translated_header_description.content) if translated_header_description else None
        else:
            translated_desc = md_page.header.description

        # Initialize new_metadata for all cases
        new_metadata = copy(md_page.header.metadata)
        
        if  md_page.header.title and self.do_translate_header_title:
            translated_header_title = await self.translate_header_item(
                md_page.header.title
            )

            # Ensure the translated title is a string
            translated_title = str(translated_header_title.content) if translated_header_title else None
        else:
            translated_title = md_page.header.title
        if 'support' in md_page.header.metadata:
            if md_page.header.metadata["support"]: #not empty
                # logging.info(f"medatada: {md_page.header.metadata}")
                support_translated = []
                for item in md_page.header.metadata["support"]:
                    support_item = await self.translate_header_item(item)
                    # Explicitly cast to string
                    support_translated.append(str(support_item.content))
                new_metadata["support"] = support_translated
                # logging.info(f"new_support: {new_metadata['support']}")
                # logging.info(f"New metadata: {new_metadata}")

        new_header = Header(
            title=translated_title,
            description=translated_desc,
            metadata=new_metadata,
            body=md_page.header.body,
        )

        return MDPage(
            filename=md_page.filename,
            content=translated_content,
            header=new_header,
        )
    

    @weave.op
    async def translate_header_item(self, header_item: str):
        """Translate the header description"""
        translated_item = await translate_content(
            header_item, self.prompt_template, **self.model_args
        )
        return translated_item


@weave.op
async def _translate_file(
    input_file: str,  # File to translate
    out_file: str,  # File to save the translated file to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
    do_translate_header_description: bool = True,  # Translate the header description
    model_args: dict = dict(model="gpt-4o", temperature=1.0),  # Model args
    max_retries: int = 3,  # Maximum number of attempts
    retry_delay: float = 3.0,  # Delay (in seconds) between retries
) -> MDPage:
    """Translate a markdown file asynchronously with retry logic"""

    if file_is_empty(input_file):
        raise ValueError(f"File {input_file} is empty")

    # Check that it is a markdown file
    if Path(input_file).suffix not in [".md", ".mdx"]:
        raise ValueError(f"File {input_file} is not a markdown file")

    out_file = Path(out_file)
    if out_file.exists() and not replace and not file_is_empty(out_file):
        logger.info(f"File {out_file} already exists. Use --replace to overwrite.")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        try:
            translator = Translator(
                config_folder=config_folder,
                language=language,
                do_translate_header_description=do_translate_header_description,
                model_args=model_args,
            )
            translation_results = await translator.translate_file(input_file, remove_comments)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(str(translation_results["translated_page"]))
            logger.debug(
                f"✅ Translated file saved to [green]{out_file}[/green]",
                extra={"markup": True},
            )
            return {
                **translation_results,
                "input_file": input_file,
                "output_file": str(out_file),
                "language": language,
            }
        except Exception as e:
            logger.error(f"❌ Attempt {attempt} failed translating {input_file}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying {input_file} in {retry_delay} seconds (Attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(retry_delay)
            else:
                return {
                    "original_page": None,
                    "translated_page": None,
                    "error": str(e),
                    "input_file": input_file,
                    "output_file": str(out_file),
                    "language": language,
                }


@weave.op
async def _translate_files(
    input_files: list[str],  # Files to translate
    input_folder: str,  # Folder where the files live
    out_folder: str,  # Folder to save the translated files to
    replace: bool = REPLACE,  # Replace existing file
    language: str = "es",  # Language to translate to
    config_folder: str = "./configs",  # Config folder
    remove_comments: bool = REMOVE_COMMENTS,  # Remove comments
    do_translate_header_description: bool = True,  # Translate the header description
    model_args: dict = dict(model="gpt-4o", temperature=1.0),  # Model args
    max_concurrent_calls: int = MAX_CONCURRENT_CALLS,  # Maximum number of concurrent calls to OpenAI
):
    input_files = [
        Path(f)
        for f in input_files
        if (Path(f).suffix in [".md", ".mdx"] and Path(f).exists())
    ]
    logger.info(
        f"Translating {len(input_files)} file" + ("s" if len(input_files) > 1 else "")
    )
    input_files.sort()
    input_folder = Path(input_folder)
    out_folder = Path(out_folder)
    if not input_folder.is_dir():
        raise ValueError(f"{input_folder} is not a folder")

    semaphore = asyncio.Semaphore(max_concurrent_calls)

    async def _translate_with_semaphore(md_file: Path):
        async with semaphore:
            out_file = out_folder / md_file.relative_to(input_folder)
            return await _translate_file(
                input_file=str(md_file),
                out_file=str(out_file),
                replace=replace,
                language=language,
                config_folder=config_folder,
                remove_comments=remove_comments,
                do_translate_header_description=do_translate_header_description,
                model_args=model_args,
            )

    start_time = time.perf_counter()
    tasks = [_translate_with_semaphore(md_file) for md_file in input_files]
    results = await gather_with_progress(tasks, "Translating files")
    duration = time.perf_counter() - start_time
    console.rule(f"Finished translating {len(input_files)} files in {duration:.2f} s")

    correct_translations = [r for r in results if r.get("error") is None]
    failed_translations = [r for r in results if r.get("error") is not None]

    if failed_translations:
        console.rule(f"Failed to translate {len(failed_translations)} files after maximum retry attempts")
        for result in failed_translations:
            console.print(f"Error translating {result['input_file']}: {result['error']}")
    else:
        console.rule("All files translated successfully")

    # dataset = to_weave_dataset(name=f"Translation-{language}", rows=correct_translations)
    # weave.publish(dataset)
    # console.rule(f"Uploaded to Weave Dataset: Translation-{language}")

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
