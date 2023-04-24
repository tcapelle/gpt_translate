import os, time
from pathlib import Path

import openai
from rich.console import Console
from rich.progress import track
from fastcore.script import call_parse, Param, store_true


from gpt_translate.roles import jpn_role

console = Console()

DOCS_DIR = Path("docs")
OUTDOCS_DIR = Path("docs_jpn")
EXTENSIONS = ["*.md", "*.mdx"]

GPT4 = "gpt-4"  # if you have access...

if not os.getenv("OPENAI_API_KEY"):
    console.print("[bold red]Please set `OPENAI_API_KEY` environment variable[/]")
    exit(1)

@call_parse
def translate_file(
    input_file: Param("File to translate", str),
    out_file: Param("File to save the translated file to", str),
    temperature: Param("Temperature of the model", float) = 0.9,
):
    console.print(f"Translating {f} to {out_file}")
    with open(input_file, "r") as f:
        history = [{"role": "system", "content":  jpn_role}, 
                   {"role": "user",   "content": "ここからが翻訳対象の文章です:\n" + f.read()}]
    t0 = time.perf_counter()
    r = openai.ChatCompletion.create(
        model=GPT4,
        messages=history,
        temperature=temperature,
        )
    out = r["choices"][0]["message"]["content"]
    total_time = time.perf_counter() - t0
    console.print(f"Time taken: {total_time:.2f} seconds")

    with open(out_file, "w") as out_f:
        console.print(f"Saving output to {out_file}")
        out_f.writelines(out)

def _get_files(path, extensions=EXTENSIONS):
    if path.is_file():
        return [path]
    files = []
    for ext in extensions:
        files.extend(list(path.rglob(ext)))
        files.sort()
    return files

@call_parse
def translate_folder(
    docs_folder: Param("Folder containing the markdown files to translate", str) = DOCS_DIR,
    out_folder: Param("Folder to save the translated files to", str) = OUTDOCS_DIR,
    replace: Param("Replace existing files", store_true) = False,

):
    "Translate a folder to Japanese using GPT-3/4"
    docs_folder = Path(docs_folder)
    console.print(f"Using {docs_folder}/ as input folder")

    out_folder = Path(out_folder)
    console.print(f"Using {out_folder}/ as output folder")

    out_folder.mkdir(exist_ok=True)

    files = _get_files(DOCS_DIR)

    console.print(f"found {len(files)} files to translate")
    
    for f in track(files, description="Translating files"):
        
        # let's make sure to keep the same folder structure
        out_file = out_folder / f.relative_to(docs_folder)
        out_file.parent.mkdir(exist_ok=True, parents=True)
        if out_file.exists() and not replace:
            console.print(f"Skipping {f} as {out_file} already exists")
        else:
            translate_file(f, out_file)