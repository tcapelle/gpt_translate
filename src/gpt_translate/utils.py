import time
import git
import logging
import weave
from datetime import datetime, timedelta
from pathlib import Path

import pydantic
import tiktoken
from openai import AsyncOpenAI
from fastcore.xtras import globtastic

# Use the OpenAI API in async mode
try:
    openai_client = AsyncOpenAI()
except Exception:
    logging.warning("Failed to initialize OpenAI client. Using a dummy client.")
    openai_client = None

MODEL = "gpt-4"


@weave.op
async def longer_create(messages=None, max_tokens=4096, **kwargs):
    """
    longer_create is a function that extends the max_tokens beyond the default 4096 by recursively calling the create method if the finish_reason is hitting the max_tokens.
    """
    if messages is None:
        messages = []

    res = await openai_client.chat.completions.create(
        messages=messages, max_tokens=max_tokens, **kwargs
    )
    message_content = res.choices[0].message.content
    logging.debug(res.usage)
    logging.debug(
        f"[blue]OpenAI response:\n{message_content[:100]}...[/blue]",
        extra={"markup": True},
    )

    finish_reason = res.choices[0].finish_reason
    if finish_reason == "length":
        # trim message to the last separator
        process_tail = remove_after(message_content)
        messages.append({"role": "assistant", "content": process_tail["text"]})
        # Recursively call the function with the last assistant's message
        logging.debug(f"Recursively calling with {messages[-1]['content'][:100]}")
        next_response = await longer_create(
            messages=messages, max_tokens=max_tokens, **kwargs
        )
        return process_tail["text"] + next_response
    else:
        return message_content


@weave.op
def remove_after(text, sep=["\n\n", "\n", ". ", ", "]):
    "Find the last `sep` from the end of the string backwards. Remove the trailing text after the line break."
    index = None
    output_text = text
    for s in sep:
        if s in text:
            index = text.rfind(s)
            output_text = text[: (index + len(s))]
            break
    else:
        s = None
    return {"text": output_text, "sep_break": s}


def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logging.debug(
            f"Function {func.__name__} took {elapsed_time:.4f} seconds to execute."
        )
        return result

    return wrapper


def file_is_empty(file: str | Path):
    return not Path(file).read_text().strip()


def get_md_files(path: Path | str, files_glob: str = "*.md", file_re: str = None):
    """
    Get a list of markdown files in the given path.
    """
    path = Path(path)
    if path.is_file():
        return [path]
    files = globtastic(path, file_glob=files_glob, file_re=file_re)
    return [Path(f) for f in files.sorted() if Path(f).exists()]


def _copy_images(src_path: Path | str, dst_path: Path | str):
    "recursively copy images from src_path to dst_path"
    src_path = Path(src_path)
    dst_path = Path(dst_path)

    # Define image file extensions
    image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"]

    for src_file in src_path.rglob("*"):
        if src_file.suffix.lower() in image_extensions:
            # Compute relative path
            rel_path = src_file.relative_to(src_path)
            # Construct destination path
            dst_file = dst_path / rel_path

            # Create parent directories if they don't exist
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            dst_file.write_bytes(src_file.read_bytes())
            logging.debug(f"Copied {src_file} to {dst_file}")


def count_tokens(chunk, model=MODEL):
    "Count the number of tokens in a chunk"
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(chunk))


def concat_md_chunks(chunks, sep="\n\n"):
    return sep.join(chunks)


def get_modified_files(repo_path: Path, since_days: int = 14, extension: str = ".md"):
    """
    Get a list of modified files in the last `since_days` days.
    """
    path = Path(repo_path).resolve().absolute()
    if not path.is_dir():
        path = path.parent
    logging.info(
        f"Searching for modified files in the last {since_days} days in: {path}"
    )
    # Open the repository
    repo = git.Repo(repo_path, search_parent_directories=True)
    repo_path = Path(repo.git_dir).parent  # this is the .git file

    logging.info(f"Repo: {repo.git_dir}")
    # Calculate the date since which to look for commits
    since_date = datetime.now() - timedelta(days=since_days)

    # Get commits since the specified date
    commits = list(repo.iter_commits(since=since_date.isoformat()))

    # Use a set to store unique modified files
    modified_files = set()

    # Iterate over the commits and collect modified files
    for commit in commits:
        for diff in commit.diff(None, create_patch=False):
            if diff.a_path:
                modified_files.add(repo_path / Path(diff.a_path))
            if diff.b_path:
                modified_files.add(repo_path / Path(diff.b_path))
    modified_files = list(
        [m for m in modified_files if m.suffix == extension and m.is_relative_to(path)]
    )
    modified_files = [f.relative_to(repo_path) for f in modified_files]
    logging.info(
        f"Found {len(modified_files)} modified files in the last {since_days} days in: {repo_path}"
    )
    return modified_files


def to_weave_dataset(name: str, rows: list) -> weave.Dataset:
    # serialize the pydantic objects that are in the dictionary:
    for result in rows:
        for k, v in result.items():
            # check if we have weave.Object or pydantic.BaseModel
            if isinstance(v, pydantic.BaseModel | weave.Object):
                result[k] = v.model_dump_json()

    # push to weave
    dataset = weave.Dataset(name=name, description="Translation files", rows=rows)
    return dataset
