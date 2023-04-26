import re
from fastcore.script import call_parse, Param, store_true
from pathlib import Path


def check_file_non_empty(file: Path):
    with open(file, "r") as f:
        lines = f.readlines()

    return bool(lines)


def split_markdown_file(file: Path, min_lines: int = 30):
    with open(file, "r") as f:
        lines = f.readlines()

    # check empty file
    if not lines:
        return []

    header_pattern = re.compile(r"^#{1,6} .*$")
    double_or_empty_line_pattern = re.compile(r"^\s*$")

    chunks = []
    chunk = []
    line_count = 0

    for line in lines:
        if line_count >= min_lines:
            if header_pattern.match(line) or double_or_empty_line_pattern.match(line):
                chunks.append("".join(chunk))
                chunk = []
                line_count = 0

        chunk.append(line)
        line_count += 1

    # Add the last chunk
    chunks.append("".join(chunk))

    # Filter out empty chunks
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

    return chunks


def count_file_lines(file: Path):
    with open(file, "r") as f:
        lines = f.readlines()

    return len(lines)


EXTENSIONS = ["*.md", "*.mdx"]


def get_md_files(path, extensions=EXTENSIONS):
    path = Path(path)
    if path.is_file():
        return [path]
    files = []
    for ext in extensions:
        files.extend(list(path.rglob(ext)))
        files.sort()
    return files


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
            maybe_remove_odd_lines(file, verbose=verbose, pct=pct)


def maybe_remove_odd_lines(path, verbose=False, pct=0.5):
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
                            

if __name__ == "__main__":
    chunks = split_markdown_file("docs/intro.md")

    print(chunks[0])
    print(len(chunks[0]))
    print(len(chunks))
