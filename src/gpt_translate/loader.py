import re, yaml
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

import weave
from pydantic import model_validator, Field


def remove_markdown_comments(content):
    # Pattern to match HTML comment blocks
    comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)

    # Remove all matched comment blocks
    cleaned_content = re.sub(comment_pattern, "", content)

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
    line_number: str

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

def represent_str(dumper, data):
    # Replace newlines with spaces and trim leading/trailing whitespace
    one_liner = re.sub(r'\n+', ' ', data).strip()
    return dumper.represent_scalar('tag:yaml.org,2002:str', one_liner)

yaml.add_representer(str, represent_str)

class Header(weave.Object):
    title: str = ""
    description: str = ""
    slug: str = ""
    displayed_sidebar: str = ""
    imports: str = ""

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
        attrs = {k: v for k, v in self.model_dump().items() if v and k != "imports"}
        if attrs:
            yaml_content = yaml.dump(attrs, sort_keys=False, allow_unicode=True, default_flow_style=False)
            parts.append(f"---\n{yaml_content.strip()}\n---")
        if self.imports:
            parts.append(self.imports)
        return "\n".join(parts).encode("utf-8").decode("utf-8")


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
    remaining_lines = lines[len(frontmatter):]
    for line in remaining_lines:
        if line.strip().startswith("import "):
            imports.append(line)
        else:
            content_lines = remaining_lines[len(imports):]
            break

    # Combine frontmatter and imports for header
    header_lines = frontmatter + imports

    # Remove trailing empty lines from header
    while header_lines and not header_lines[-1].strip():
        header_lines.pop()

    header = "\n".join(header_lines).rstrip()
    content = "\n".join(content_lines).strip()

    return {"header": header, "content": content}


@weave.op
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
    raw_content: str
    header: Header = Field(default=None)
    links: list[MDLink] = Field(default=None)
    content: str = Field(init=False)

    @model_validator(mode="before")
    def initialize_fields(cls, values):
        raw_content = values.get("raw_content", "")
        if "header" not in values or values["header"] is None:
            extracted = extract_header(raw_content)
            header = extracted["header"]
            content = extracted["content"]
            values["header"] = Header.from_string(header)
            values["content"] = content
        else:
            values["content"] = raw_content[len(str(values["header"])) :]
        return values

    @model_validator(mode="after")
    def set_links(self):
        self.links = find_links(self.raw_content, self.filename)
        return self

    @weave.op
    def from_translated(
        self, translated_content: str, fix_links: bool = True
    ) -> "MDPage":
        translated_page = MDPage(
            filename=self.filename, raw_content=f"{self.header}\n{translated_content}"
        )
        if fix_links:
            translated_page.update_links(self.links)
        return translated_page

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
            self.links = self.find_links(self.raw_content)
        else:
            self.links = new_links

    def __str__(self):
        "Concatenate header and content"
        if str(self.header).strip():
            return f"{self.header}\n\n{self.content}"
        return str(self.content)


