import os, time
from textwrap import dedent
from pathlib import Path

import openai
from rich.console import Console
from rich.progress import track
from rich.markdown import Markdown
from fastcore.script import call_parse, Param, store_true


from gpt_translate.roles import translation_roles, filter_dictionary
from gpt_translate.utils import split_markdown_file, get_md_files

console = Console()

DOCS_DIR = Path("docs")
OUTDOCS_DIR = Path("docs_jpn")
MAX_CHUNK_LENGTH = 50
MIN_LINE = 40

GPT4 = "gpt-4"  # if you have access...
GPT3 = "gpt-3.5-turbo"
# GPT4 = "gpt-4-32k"


def parse_model_name(model):
    "Parse the model name and return the pricing"
    if "4" in model:
        return GPT4
    elif "3.5" in model:
        return GPT3


if not os.getenv("OPENAI_API_KEY"):
    console.print("[bold red]Please set `OPENAI_API_KEY` environment variable[/]")
    exit(1)


def call_model(model, query, temperature=0.7, language="jp"):
    "Call the model and return the output"
    role = translation_roles[language]

    # remove unnecessary dictionary entries from the role
    filtered_dict = filter_dictionary(query, role["dictionary"])
    system_role = role["system"] + filtered_dict

    history = [
        {"role": "system", "content": system_role},
        {"role": "user", "content": role["prompt"] + "\n" + query},
    ]
    t0 = time.perf_counter()
    r = openai.ChatCompletion.create(
        model=parse_model_name(model),
        messages=history,
        temperature=temperature,
    )
    out = r["choices"][0]["message"]["content"]
    total_time = time.perf_counter() - t0
    console.print(f"Time taken: {total_time:.2f} seconds")
    ptokens, ctokens = r["usage"]["prompt_tokens"], r["usage"]["completion_tokens"]
    console.print(f"Tokens: {ptokens} / {ctokens}")
    console.print(f"Cost: ${(ptokens*0.03+ctokens*0.06)/1000}")
    return out


def _translate_file(
    input_file,
    out_file,
    temperature=0.9,
    replace=False,
    language="jp",
    model=GPT4,
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
    chunks = split_markdown_file(input_file, min_lines=MIN_LINE)
    out = []
    if chunks:
        if len(chunks[0].split("\n")) > MAX_CHUNK_LENGTH:
            console.print(
                f"Skipping {input_file} as it has a chunk with more than {MAX_CHUNK_LENGTH} lines"
            )
            return

        for i, chunk in enumerate(chunks):
            console.print(f"Translating chunk {i+1}/{len(chunks)}")
            try:
                if verbose:
                    console.print(f"Input Text: \n{chunk}")
                out.append(
                    call_model(model, chunk, temperature=temperature, language=language)
                )
                if verbose:
                    console.print(f"Translation: \n{out[-1]}")
            except Exception as e:
                if "currently overloaded" in str(e):
                    console.print("Server overloaded, waiting for 30 seconds")
                    time.sleep(30)
                    out.append(
                        call_model(
                            model, chunk, temperature=temperature, language=language
                        )
                    )
                raise e

        # merge the chunks
        out = "\n".join(out)
    else:
        out = ""

    with open(out_file, "w") as out_f:
        console.print(f"Saving output to {out_file}")
        out_f.writelines(out)


@call_parse
def translate_file(
    input_file: Param("File to translate", str),
    out_file: Param("File to save the translated file to", str),
    temperature: Param("Temperature of the model", float) = 0.9,
    replace: Param("Replace existing file", store_true) = False,
    language: Param("Language to translate to", str) = "jp",
    model: Param("Model to use", str) = GPT4,
    verbose: Param("Print the output", store_true) = False,
):
    try:
        _translate_file(
            Path(input_file),
            Path(out_file),
            temperature=temperature,
            replace=replace,
            language=language,
            model=model,
            verbose=verbose,
        )
    except Exception as e:
        console.print(f"[bold red]Error while translating {input_file}[/]")
        console.print(e)


@call_parse
def translate_folder(
    docs_folder: Param("Folder containing markdown files to translate", str) = DOCS_DIR,
    out_folder: Param("Folder to save the translated files to", str) = OUTDOCS_DIR,
    replace: Param("Replace existing files", store_true) = False,
    language: Param("Language to translate to", str) = "jn",
    model: Param("Model to use", str) = GPT4,
    verbose: Param("Print the output", store_true) = False,
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

    files = get_md_files(docs_folder)

    console.print(f"found {len(files)} files to translate")

    for input_file in track(files, description="Translating files"):
        # let's make sure to keep the same folder structure
        out_file = out_folder / input_file.relative_to(docs_folder)
        try:
            _translate_file(
                input_file,
                out_file,
                replace=replace,
                language=language,
                model=model,
                verbose=verbose,
            )
        except Exception as e:
            out_file.unlink()
            console.print(f"[bold red]Error while translating {input_file}[/]")
            console.print(e)
