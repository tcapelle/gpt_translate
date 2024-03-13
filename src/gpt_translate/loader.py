import re, yaml
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field

log = logging.getLogger(__name__)

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
@dataclass
class MDLlink:
    title: str
    target: str
    line_number: str

    def __str__(self):
        return f"{self.line_number:>4}: [{self.title}]({self.target})"
    
    def __eq__(self, other):
        return self.target == other.target

def extract_markdown_links(content):
    # This regular expression matches the Markdown link syntax
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    links = []
    for i, line in enumerate(content.split("\n")):
        matches = re.findall(link_pattern, line)
        for title, target in matches:
            links.append(MDLlink(title, target, i+1))
    return links

@dataclass
class Header:
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
            if line.strip() == '---':
                yaml_start = not yaml_start
                continue
            if yaml_start:
                yaml_lines.append(line)
            else:
                import_lines.append(line)

        # Parse the YAML content
        attributes = yaml.safe_load("\n".join(yaml_lines))
        # Rejoin the import lines into a single string
        imports = "\n".join(import_lines).strip()
        if not attributes and not imports:
            return ""
        return cls(**attributes, imports=imports)
    
    def __repr__(self) -> str:
        return str(self)
    
    def __str__(self) -> str:
        # Convert the dataclass fields to a dictionary, then to a YAML-formatted string
        # Exclude the 'imports' field for the YAML content
        attrs = {k: v for k, v in asdict(self).items() if v and k != "imports"}
        yaml_content = yaml.safe_dump(attrs, sort_keys=False)
        # Include the imports at the beginning if any
        import_content = f"{self.imports}\n" if self.imports else ""
        return f"---\n{yaml_content}---\n{import_content}"

def extract_header(content):
    "Extract header from a markdown file, everything before the title and the rest of the content"
    header = ""
    for line in content.split("\n"):
        if line.startswith("# "):
            break
        header += line + "\n"
    return header, content[len(header):]

@dataclass
class MDPage:
    title: str = "Title"
    raw_content: str = "Content"
    header: str = "Header"
    links: list[MDLlink] = None
    content: str = field(init=False)
    
    def __post_init__(self):
        header, self.content = extract_header(self.raw_content)
        self.header = Header.from_string(header)
        self.links = self.find_links()
    
    @classmethod
    def create(cls, title, md_content):
        return cls(title=title, raw_content=md_content)

    def from_translated(self, translated_content, fix_links=True):
        translated_page = MDPage.create(self.title, f"{self.header}\n{translated_content}")
        if fix_links:
            translated_page.update_links(self.links)
        return translated_page

    def find_links(self):
        """
        Finds all Markdown links in the content.
        :return: list of tuples, each containing (link text, URL).
        """
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = []
        for i, line in enumerate(self.raw_content.split("\n")):
            matches = re.findall(link_pattern, line)
            for title, target in matches:
                links.append(MDLlink(title, target, i+1))
        return links
    
    def update_links(self, new_links, targets_only=True):
        "Update the links in the content"
        if len(new_links) == len(self.links):
            log.error(f"The following links don't match: {new_links} vs {self.links}")
            raise ValueError(f"Number of links don't match: {len(new_links)} vs {len(self.links)}")
        log.debug(f"Maybe updating links in {self.title}")
        for old_link, new_link in zip(self.links, new_links):
            if old_link.target != new_link.target:
                log.debug(f"Replacing {old_link} with {new_link}")
                self.content = self.content.replace(old_link.target, new_link.target)
        if targets_only:
            self.links = self.find_links()
        else:
            self.links = new_links
    
    def __str__(self):
        "Concatenate header and content"
        return f"{self.header}\n{self.content}"
        
