from pathlib import Path
import re


def remove_markdown_comments(content):
    # Pattern to match HTML comment blocks
    comment_pattern = re.compile(r'<!--.*?-->', re.DOTALL)

    # Remove all matched comment blocks
    cleaned_content = re.sub(comment_pattern, '', content)

    return cleaned_content


def split_markdown(content):
    header_pattern = re.compile(r'^(#{1,6} .+)$', re.MULTILINE)
    code_block_pattern = re.compile(r'^```')

    chunks = []
    current_chunk = []
    in_code_block = False

    for line in content.split('\n'):
        if code_block_pattern.match(line):
            in_code_block = not in_code_block

        # Split at headers, only if not within a code block
        if header_pattern.match(line) and not in_code_block:
            if current_chunk:
                # Add the current chunk to chunks
                chunks.append('\n'.join(current_chunk).strip())
                current_chunk = [line]
                in_code_block = False
            else:
                current_chunk.append(line)
        else:
            current_chunk.append(line)

    # Add the last chunk if not empty
    if current_chunk:
        chunks.append('\n'.join(current_chunk).strip())

    return chunks

