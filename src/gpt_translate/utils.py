import time
import git
import logging
import asyncio
import weave
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from pathlib import Path

import tiktoken
from litellm import acompletion
from fastcore.xtras import globtastic
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, TaskID, TimeElapsedColumn, BarColumn, TextColumn, MofNCompleteColumn
from typing import Optional

MODEL = "gpt-4o"

# Console for Rich formatting - shared across the application
console = Console()

# Shared logger instance for the application
# Note: The logger configuration is handled by the CLI setup_logging function
logger = logging.getLogger("gpt_translate")


@weave.op
async def gather_with_progress(
    tasks: list,
    description: str = "Processing",
    progress: Optional[Progress] = None
) -> list:
    """
    Execute multiple async tasks with a Rich progress bar.
    
    Args:
        tasks: List of async tasks to execute
        description: Description to show in the progress bar
        progress: Rich Progress object. If None, creates a default one.
        
    Returns:
        List of results from completed tasks. Failed tasks return {"error": "error_message"}
    """
    if not tasks:
        return []
    
    # Create default progress if none provided
    if progress is None:
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as default_progress:
            return await _execute_tasks_with_progress(tasks, description, default_progress)
    else:
        # Use provided progress object (don't manage its lifecycle)
        return await _execute_tasks_with_progress(tasks, description, progress)


async def _execute_tasks_with_progress(tasks: list, description: str, progress: Progress) -> list:
    """
    Internal function to execute tasks with a given progress object.
    
    Args:
        tasks: List of async tasks to execute
        description: Description for the progress task
        progress: Active Progress object
        
    Returns:
        List of results from completed tasks
    """
    task_id = progress.add_task(description, total=len(tasks))
    
    # Use a proper mapping instead of mutating task objects
    task_to_index = {}
    results = [None] * len(tasks)
    asyncio_tasks = []
    
    try:
        # Create all tasks
        for i, task in enumerate(tasks):
            asyncio_task = asyncio.create_task(task)
            task_to_index[asyncio_task] = i
            asyncio_tasks.append(asyncio_task)
        
        pending_tasks = set(asyncio_tasks)
        
        while pending_tasks:
            # Use wait to get completed tasks
            done, pending_tasks = await asyncio.wait(
                pending_tasks, 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for completed_task in done:
                task_index = task_to_index[completed_task]
                
                try:
                    result = await completed_task
                    results[task_index] = result
                except asyncio.CancelledError:
                    results[task_index] = {"error": "Task was cancelled"}
                    raise  # Re-raise cancellation
                except Exception as e:
                    # Handle errors by storing them in the result
                    logger.exception(f"Task {task_index} failed: {e}")
                    results[task_index] = {"error": str(e)}
                
                progress.update(task_id, advance=1)
        
        return results
        
    except Exception:
        # Cancel any remaining tasks on error
        for task in asyncio_tasks:
            if not task.done():
                task.cancel()
        raise


@weave.op
async def longer_create(messages=None, max_tokens=4096, **kwargs):
    """
    longer_create is a function that extends the max_tokens beyond the default 4096 by recursively calling the completion method if the finish_reason is hitting the max_tokens.
    """
    if messages is None:
        messages = []

    res = await acompletion(
        messages=messages,
        max_tokens=max_tokens,
        **kwargs,
    )
    message_content = res.choices[0].message.content
    logging.debug(res.usage)
    logging.debug(
        f"[blue]Litellm response:\n{message_content[:100]}...[/blue]",
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
    def _process_row(row):
        return {
            "input_file": row["input_file"],
            "output_file": row["output_file"],
            "language": row["language"],
            "original_doc": row["original_page"].content,
            "translated_doc": row["translated_page"].content,
        }
    processed_rows = []
    for row in rows:
        processed_rows.append(_process_row(row))

    # push to weave
    dataset = weave.Dataset(name=name, description="Translation files", rows=processed_rows)
    return dataset
