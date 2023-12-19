import re
import time

import tiktoken

from fastcore.script import call_parse, Param, store_true
from fastcore.xtras import globtastic

from pathlib import Path


def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.4f} seconds to execute.")
        return result
    return wrapper

def check_file_non_empty(file: Path):
    with open(file, "r") as f:
        lines = f.readlines()

    return bool(lines)


def get_md_files(path: Path | str, files_glob: str = "*.md", file_re: str = None):
    path = Path(path)
    if path.is_file():
        return [path]
    files = globtastic(path, file_glob=files_glob, file_re=file_re)
    return [Path(f) for f in files.sorted()]


@call_parse
def delete_empty_files(
    path: Param("Path to delete empty files from", str),
    verbose: Param("Verbose", store_true) = False,
):
    for f in get_md_files(path):
        if not check_file_non_empty(f):
            if verbose:
                print(f"Deleting {f}")
            f.unlink()


def remove_newline(path, verbose=False, pct=0.5):
    for file in get_md_files(path):
        if check_file_non_empty(file):
            _maybe_remove_odd_lines(file, verbose=verbose, pct=pct)


def _maybe_remove_odd_lines(path, verbose=False, pct=0.5):
    with open(path, "r") as f:
        lines = f.readlines()
    if len([line for line in lines if line == "\n"]) / len(lines) > pct:
        if verbose:
            print(f"Removing odd lines from {path}")
        with open(path, "w") as f:
            for i in range(len(lines)):
                if i % 2 == 0:
                    f.write(lines[i])
    else:
        if verbose:
            print(f"Skipping: {path}")

def count_tokens(chunk, model="gpt-4"):
    "Count the number of tokens in a chunk"
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(chunk))

def concat_md_chunks(chunks, sep="\n\n"):
    return sep.join(chunks)