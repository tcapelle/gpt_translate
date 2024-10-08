import re
import json

import weave
from gpt_translate.loader import MDPage
from gpt_translate.utils import openai_client


class LinksValidation(weave.Object):
    links_match: bool
    missing_links: list
    extra_links: list
    total_links: int

@weave.op
def validate_links(original_page: MDPage, translated_page: MDPage):
    """
    Validate that the links in the original page are the same as the links in the translated page.
    """
    original_links = original_page.links
    translated_links = translated_page.links

    missing_links = [link for link in original_links if link not in translated_links]
    extra_links = [link for link in translated_links if link not in original_links]
    return LinksValidation(
        links_match=len(missing_links) == 0 and len(extra_links) == 0,
        missing_links=[l.target for l in missing_links],
        extra_links=[l.target for l in extra_links],
        total_links=len(original_links),
    )


class HeadersValidation(weave.Object):
    title_match: bool
    description_match: bool
    slug_match: bool
    displayed_sidebar_match: bool
    imports_match: bool

@weave.op
def validate_headers(original_page: MDPage, translated_page: MDPage):
    """
    Validate that the headers in the original page are the same as the headers in the translated page.
    """
    original_header = original_page.header
    translated_header = translated_page.header
    title_match = original_header.title == translated_header.title
    description_match = original_header.description == translated_header.description
    slug_match = original_header.slug == translated_header.slug
    displayed_sidebar_match = (
        original_header.displayed_sidebar == translated_header.displayed_sidebar
    )
    imports_match = original_header.imports == translated_header.imports
    return HeadersValidation(
        title_match=title_match,
        description_match=description_match,
        slug_match=slug_match,
        displayed_sidebar_match=displayed_sidebar_match,
        imports_match=imports_match,
    )


def _validate_tabs_format(content: str) -> bool:
    tab_pattern = re.compile(
        r"""
        <Tabs\s*[^>]*>\s*
        (?:<TabItem\s*[^>]*>\s*.*?\s*</TabItem>\s*)+
        </Tabs>
        """,
        re.DOTALL | re.VERBOSE,
    )
    return bool(tab_pattern.search(content))


@weave.op
def validate_tabs(translated_page: MDPage):
    """
    Validate the Tabs in the docosaurus format
    """
    content = translated_page.content

    return {"tabs_format_valid": _validate_tabs_format(content)}
 

class LLMJudge(weave.Model):
    system_prompt: str
    evaluation_prompt: str
    model_args: dict

    @weave.op
    async def predict(self, original_page: MDPage, translated_page: MDPage):
        """Evaluate the translation"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.evaluation_prompt.format(
                original_page=original_page.content, 
                translated_page=translated_page.content)},
        ]
        res = openai_client.chat.completions.create(
            messages=messages,
            **self.model_args,
            response_format={"type": "json_object"},
        )
        extracted = res.choices[0].message.content
        analysis = json.loads(extracted)
        return analysis