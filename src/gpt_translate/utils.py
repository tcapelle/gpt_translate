import time
import git
import logging
import weave
from datetime import datetime, timedelta
from pathlib import Path

from fastcore.xtras import globtastic
import tiktoken

MODEL = "gpt-4"


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
