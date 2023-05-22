import os, time
from textwrap import dedent
from pathlib import Path
from typing import Any


from rich.console import Console
from rich.progress import track
from rich.markdown import Markdown
from fastcore.script import call_parse, Param, store_true

from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain

from wandb.integration.langchain import WandbTracer


from gpt_translate.utils import get_md_files
from gpt_translate.roles import CHAT_PROMPT, DICTIONARIES, filter_dictionary

console = Console()

DOCS_DIR = Path("docs")
OUTDOCS_DIR = Path("docs_ja")
MAX_CHUNK_TOKENS = 1000
TIMEOUT = 600
TEMPERATURE = 0.7

GPT4 = "gpt-4"  # if you have access...
GPT3 = "gpt-3.5-turbo"
# GPT4 = "gpt-4-32k"

LANGUAGES = dict(ja="Japanese", en="English", es="Spanish")


def parse_model_name(model):
    "Parse the model name and return the pricing"
    if "4" in model:
        return GPT4
    elif "3.5" in model:
        return GPT3

class MarkdownTextSplitter(RecursiveCharacterTextSplitter):
    """A super basic Splitter that splits on newlines and spaces."""

    def __init__(self, **kwargs: Any):
        """Initialize a MarkdownTextSplitter."""
        separators = [
            "\n\n",
            "\n",
            " ",
        ]
        super().__init__(separators=separators, **kwargs)


def get_translate_chain(
    model_name=GPT3, chat_prompt=CHAT_PROMPT, temperature=TEMPERATURE
):
    "Get a translation chain"
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Please set `OPENAI_API_KEY` environment variable[/]")
        exit(1)
    chat = ChatOpenAI(
        model_name=model_name, temperature=temperature, request_timeout=TIMEOUT
    )
    chain = LLMChain(llm=chat, prompt=chat_prompt)
    return chain


class IdentityChain:
    def __init__(self):
        pass

    def run(self, text=None, **kwargs):
        return text


def get_identity_chain():
    return IdentityChain()


def _translate_file(
    input_file,
    out_file,
    temperature=TEMPERATURE,
    max_chunk_tokens=MAX_CHUNK_TOKENS,
    replace=False,
    language="ja",
    model=GPT3,
    verbose=False,
):
    "Translate a file to Japanese using GPT-3/4"

    if Path(out_file).exists() and not replace:
        console.print(f"Skipping {input_file} as {out_file} already exists")
        return

    # create the output file
    out_file.parent.mkdir(exist_ok=True, parents=True)
    out_file.touch()

    console.print(f"Translating {input_file} to {out_file}")

    docs = TextLoader(input_file).load()

    markdown_splitter = MarkdownTextSplitter(
        chunk_size=max_chunk_tokens, chunk_overlap=0
    )
    chunks = markdown_splitter.split_documents(docs)

    chain = get_translate_chain(model_name=model, temperature=temperature)
    # chain = get_identity_chain()

    out = []

    for i, chunk in enumerate(chunks):
        console.print(f"Translating chunk {i+1}/{len(chunks)}")

        # text to translate
        query = chunk.page_content

        # filter dictionary with words from the text
        translation_dict = filter_dictionary(query, DICTIONARIES[language])
        try:
            if verbose:
                console.print(Markdown(f"Input Text:\n==============\n{chunk}"))
            out.append(
                chain.run(
                    input_language="English",
                    output_language=LANGUAGES[language],
                    dictionary=translation_dict,
                    text=query,
                )
            )
            if verbose:
                console.print(Markdown(f"Translation:\n==============\n{out[-1]}"))
        except Exception as e:
            if "currently overloaded" in str(e):
                console.print("Server overloaded, waiting for 30 seconds")
                time.sleep(30)
                out.append(
                    chain.run(
                        input_language="English",
                        output_language=LANGUAGES[language],
                        dictionary=translation_dict,
                        text=query,
                    )
                )
            raise e

    # merge the chunks
    out = "\n\n".join(out)

    with open(out_file, "w") as out_f:
        console.print(f"Saving output to {out_file}")
        out_f.writelines(out)


@call_parse
def translate_file(
    input_file: Param("File to translate", str),
    out_file: Param("File to save the translated file to", str),
    temperature: Param("Temperature of the model", float) = TEMPERATURE,
    max_chunk_tokens: Param("Max tokens per chunk", int) = MAX_CHUNK_TOKENS,
    replace: Param("Replace existing file", store_true) = False,
    language: Param("Language to translate to", str) = "ja",
    model: Param("Model to use", str) = GPT3,
    verbose: Param("Print the output", store_true) = False,
):
    try:
        WandbTracer.init({"project": "docs_translate", "group": language})
        _translate_file(
            Path(input_file),
            Path(out_file),
            temperature=temperature,
            max_chunk_tokens=max_chunk_tokens,
            replace=replace,
            language=language,
            model=model,
            verbose=verbose,
        )
        WandbTracer.finish()
    except Exception as e:
        console.print(f"[bold red]Error while translating {input_file}[/]")
        console.print(e)
        raise e


@call_parse
def translate_folder(
    docs_folder: Param("Folder containing markdown files to translate", str) = DOCS_DIR,
    out_folder: Param("Folder to save the translated files to", str) = OUTDOCS_DIR,
    temperature: Param("Temperature of the model", float) = TEMPERATURE,
    max_chunk_tokens: Param("Max tokens per chunk", int) = MAX_CHUNK_TOKENS,
    replace: Param("Replace existing files", store_true) = False,
    language: Param("Language to translate to", str) = "jn",
    model: Param("Model to use", str) = GPT4,
    verbose: Param("Print the output", store_true) = False,
    file_ext: Param("File extension to filter files", str) = "*.md",
    file_re: Param("Regex to filter files", str) = None,
):
    "Translate a folder to Japanese using GPT-3/4"
    docs_folder = Path(docs_folder)
    out_folder = Path(out_folder)
    console.print(
        dedent(
            f"""
        ======================================
        Using {docs_folder}/ as input folder
        Using {out_folder}/ as output folder
        model = {model}
        language = {language}
        ======================================"""
        )
    )

    out_folder.mkdir(exist_ok=True)

    files = get_md_files(docs_folder, files_glob=file_ext, file_re=file_re)

    console.print(f"found {len(files)} files to translate")

    for input_file in track(files, description="Translating files"):
        # let's make sure to keep the same folder structure
        out_file = out_folder / input_file.relative_to(docs_folder)
        try:
            _translate_file(
                input_file,
                out_file,
                temperature=temperature,
                max_chunk_tokens=max_chunk_tokens,
                replace=replace,
                language=language,
                model=model,
                verbose=verbose,
            )
        except Exception as e:
            out_file.unlink()
            console.print(f"[bold red]Error while translating {input_file}[/]")
            console.print(e)
