import re
from pathlib import Path

def split_markdown_file(file: Path,  min_lines:int=50):
    with open(file, 'r') as f:
        lines = f.readlines()

    header_pattern = re.compile(r'^#{1,6} .*$')

    chunks = []
    chunk = []
    line_count = 0

    for line in lines:
        if header_pattern.match(line) and line_count >= min_lines:
            chunks.append("".join(chunk))
            chunk = []
            line_count = 0

        chunk.append(line)
        line_count += 1

    # Add the last chunk
    chunks.append("\n".join(chunk))

    # Filter out empty chunks
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

    return chunks

def count_file_lines(file: Path):
    with open(file, 'r') as f:
        lines = f.readlines()

    return len(lines)

if __name__ == "__main__":
    chunks = split_markdown_file("docs/intro.md")
    print(len(chunks))
    print(chunks[0])