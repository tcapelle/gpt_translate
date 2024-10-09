import re
import yaml
import logging
from typing import Optional
from dataclasses import dataclass, asdict

import weave
from pydantic import model_validator, Field


def remove_markdown_comments(content):
    # Pattern to match HTML comment blocks
    comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)

    # Remove all matched comment blocks
    cleaned_content = re.sub(comment_pattern, "\n", content)

    return cleaned_content


def split_markdown(content):
    header_pattern = re.compile(r"^(#{1,6} .+)$", re.MULTILINE)
    code_block_pattern = re.compile(r"^```")

    chunks = []
    current_chunk = []
    in_code_block = False

    for line in content.split("\n"):
        if code_block_pattern.match(line):
            in_code_block = not in_code_block

        # Split at headers, only if not within a code block
        if header_pattern.match(line) and not in_code_block:
            if current_chunk:
                # Add the current chunk to chunks
                chunks.append("\n".join(current_chunk).strip())
                current_chunk = [line]
                in_code_block = False
            else:
                current_chunk.append(line)
        else:
            current_chunk.append(line)

    # Add the last chunk if not empty
    if current_chunk:
        chunks.append("\n".join(current_chunk).strip())

    return chunks


@dataclass
class MDLink:
    title: str
    target: str
    filename: str
    line_number: int

    def __str__(self):
        return f"{self.filename}:{self.line_number:>4}: [{self.title}]({self.target})"

    def __eq__(self, other):
        "We only care to know if the link is still pointing to the same place"
        return self.target == other.target


def extract_markdown_links(filename, content):
    # This regular expression matches the Markdown link syntax
    link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    links = []
    for i, line in enumerate(content.split("\n")):
        matches = re.findall(link_pattern, line)
        for title, target in matches:
            links.append(MDLink(title, target, filename, i + 1))
    return links


@dataclass
class Header:
    title: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    displayed_sidebar: Optional[str] = None
    toc_max_heading_level: Optional[int] = None
    sidebar_position: Optional[int] = None

    imports: Optional[str] = None

    @classmethod
    def from_string(cls, input_string: str):
        # Split the string into lines
        lines = input_string.splitlines()

        # Identify and separate the import lines and the YAML content
        import_lines = []
        yaml_lines = []
        yaml_start = False
        for line in lines:
            if line.strip() == "---":
                yaml_start = not yaml_start
                continue
            if yaml_start:
                yaml_lines.append(line)
            else:
                import_lines.append(line)

        # Parse the YAML content
        attributes = yaml.safe_load("\n".join(yaml_lines)) or {}
        # Rejoin the import lines into a single string
        imports = "\n".join(import_lines).strip()
        if not attributes and not imports:
            return cls()
        return cls(**attributes, imports=imports)

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        parts = []
        attrs = {k: v for k, v in asdict(self).items() if v and k != "imports"}
        # sort by key
        if attrs:
            attr_parts = ""
            attr_parts += "---\n"
            for key, value in attrs.items():
                # let's handle if value is a multiline string by removing the line breaks
                if isinstance(value, str):
                    value = value.strip().replace("\n", " ")
                attr_parts += f"{key}: {value}\n"
            attr_parts += "---"
            parts.append(attr_parts)
        if self.imports:
            parts.append(self.imports)
        header = "\n".join(parts).encode("utf-8").decode("utf-8")
        return header


@weave.op
def extract_header(content: str) -> dict:
    "Extract header from a markdown file, including YAML frontmatter and imports"
    lines = content.split("\n")
    frontmatter = []
    imports = []
    content_lines = []
    in_frontmatter = False

    # Extract frontmatter
    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                frontmatter.append(line)
            else:
                frontmatter.append(line)
                break
        elif in_frontmatter:
            frontmatter.append(line)
        else:
            break

    # Extract imports and content
    remaining_lines = lines[len(frontmatter) :]
    for line in remaining_lines:
        if line.strip().startswith("import "):
            imports.append(line)
        else:
            content_lines = remaining_lines[len(imports) :]
            break

    # Combine frontmatter and imports for header
    header_lines = frontmatter + imports

    # Remove trailing empty lines from header
    while header_lines and not header_lines[-1].strip():
        header_lines.pop()

    header = "\n".join(header_lines).rstrip()
    content = "\n".join(content_lines).strip()

    return {"header": header, "content": content}


def find_links(raw_content: str, filename: str) -> list[MDLink]:
    """
    Finds all Markdown links in the content.
    :return: list of tuples, each containing (link text, URL).
    """
    link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    links = []
    for i, line in enumerate(raw_content.split("\n")):
        matches = re.findall(link_pattern, line)
        for title, target in matches:
            links.append(MDLink(title, target, filename, i + 1))
    return links


class MDPage(weave.Object):
    filename: str
    content: str
    header: Header
    links: list[MDLink] | None = Field(default=None)

    @model_validator(mode="after")
    def set_links(self):
        if self.links is None:
            self.links = find_links(self.content, self.filename)
        return self

    @classmethod
    def from_raw_content(cls, filename: str, raw_content: str) -> "MDPage":
        extracted = extract_header(raw_content)
        header = extracted["header"]
        content = extracted["content"]
        header = Header.from_string(header)
        return cls(
            filename=filename,
            content=content,
            header=header,
        )

    @weave.op
    def update_links(self, new_links: list[MDLink], targets_only=True) -> None:
        "Update the links in the content"
        if len(new_links) == len(self.links):
            logging.error(
                f"The following links don't match: {new_links} vs {self.links}"
            )
            raise ValueError(
                f"Number of links don't match: {len(new_links)} vs {len(self.links)}"
            )
        logging.debug(f"Maybe updating links in {self.filename}")
        for old_link, new_link in zip(self.links, new_links):
            if old_link.target != new_link.target:
                logging.debug(f"Replacing {old_link} with {new_link}")
                self.content = self.content.replace(old_link.target, new_link.target)
        if targets_only:
            self.links = self.find_links(self.content)
        else:
            self.links = new_links

    def __str__(self):
        "Concatenate header and content"
        if str(self.header).strip():
            return f"{self.header}\n\n{self.content}"
        return str(self.content)
