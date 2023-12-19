import time
from pathlib import Path

from fastcore.xtras import globtastic
import tiktoken

MODEL = "gpt-4"

def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.4f} seconds to execute.")
        return result
    return wrapper

def file_is_empty(file: Path):
    with open(file, 'r', encoding='utf-8') as file:
        content = file.read()
        return not content.strip()


def get_md_files(path: Path | str, files_glob: str = "*.md", file_re: str = None):
    path = Path(path)
    if path.is_file():
        return [path]
    files = globtastic(path, file_glob=files_glob, file_re=file_re)
    return [Path(f) for f in files.sorted()]


def count_tokens(chunk, model=MODEL):
    "Count the number of tokens in a chunk"
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(chunk))

def concat_md_chunks(chunks, sep="\n\n"):
    return sep.join(chunks)
