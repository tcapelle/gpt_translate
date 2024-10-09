import asyncio
import re
import json
import logging
from pathlib import Path
from typing import Any
import weave
from gpt_translate.configs import EvalConfig
from gpt_translate.loader import MDPage
from gpt_translate.utils import openai_client
from gpt_translate.prompts import PromptTemplate


class LinksValidation(weave.Object):
    links_match: bool
    missing_links: list
    extra_links: list
    total_links: int

class HeadersValidation(weave.Object):
    title_match: bool
    description_match: bool
    slug_match: bool
    displayed_sidebar_match: bool
    imports_match: bool


@weave.op
def validate_links(original_page: MDPage, translated_page: MDPage, model_output: Any) -> LinksValidation:
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


@weave.op
def validate_headers(original_page: MDPage, translated_page: MDPage, model_output: Any) -> HeadersValidation:
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


@weave.op
def validate_tabs(translated_page: MDPage, model_output: Any) -> bool:
    """
    Validate the Tabs in the docosaurus format
    """
    tab_pattern = re.compile(
        r"""
        <Tabs\s*[^>]*>\s*
        (?:<TabItem\s*[^>]*>\s*.*?\s*</TabItem>\s*)+
        </Tabs>
        """,
        re.DOTALL | re.VERBOSE,
    )

    results = bool(tab_pattern.search(translated_page.content))

    return {"tabs_format_valid": _validate_tabs_format(results)}


class LLMJudge(weave.Model):
    system_prompt: str
    evaluation_prompt: str
    model_args: dict

    @weave.op
    async def predict(self, original_page: MDPage, translated_page: MDPage):
        """Evaluate the translation"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": self.evaluation_prompt.format(
                    original_page=original_page.content,
                    translated_page=translated_page.content,
                ),
            },
        ]
        res = await openai_client.chat.completions.create(
            messages=messages,
            **self.model_args,
            response_format={"type": "json_object"},
        )
        extracted = res.choices[0].message.content
        analysis = json.loads(extracted)
        return {"analysis": analysis, "translated_page": translated_page}


class Evaluator:
    def __init__(self, config: EvalConfig):
        self.config = config
        self.dataset = self.get_dataset()
        self.model_args = {
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        self.setup_judge()

    def _load_prompts(self):
        config_folder = Path(self.config.config_folder)
        language = self.config.language
        prompt_template = PromptTemplate.from_files(
            config_folder / "system_prompt.txt",
            config_folder / "human_prompt.txt",
            config_folder / f"language_dicts/{language}.yaml",
            config_folder / "evaluation_prompt.txt",
        )
        return prompt_template

    def setup_judge(self):
        prompt_template = self._load_prompts()
        self.judge = LLMJudge(
            system_prompt=prompt_template.system_prompt,
            evaluation_prompt=prompt_template.evaluation_prompt,
            model_args=self.model_args,
        )

    def get_dataset(self):
        logging.info(f"Getting dataset: {self.config.eval_dataset}")
        dataset = weave.ref(self.config.eval_dataset).get()

        def deserialize(md_page):
            """md_page is a string of a dictionary"""
            return MDPage.model_validate(json.loads(md_page))

        return [
            {
                "original_page": deserialize(row["original_page"]),
                "translated_page": deserialize(row["translated_page"]),
            }
            for row in dataset.rows
        ]

    def evaluate(self):
        evaluation = weave.Evaluation(
            dataset=self.dataset,
            scorers=[
                validate_links,
                validate_headers,
                validate_tabs,
            ],
        )
        asyncio.run(evaluation.evaluate(self.judge))
