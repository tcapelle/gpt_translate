import asyncio
import re
import json
import logging
import yaml
from pathlib import Path
from typing import Any, Callable
import weave
from gpt_translate.configs import EvalConfig
from gpt_translate.loader import MDPage
from gpt_translate.utils import openai_client
from gpt_translate.prompts import PromptTemplate


@weave.op
def validate_links(original_page: MDPage, translated_page: MDPage, model_output: Any) -> dict:
    """
    Validate that the links in the original page are the same as the links in the translated page.
    """
    original_links = original_page.links
    translated_links = translated_page.links

    missing_links = [link for link in original_links if link not in translated_links]
    extra_links = [link for link in translated_links if link not in original_links]
    return dict(
        links_match=len(missing_links) == 0 and len(extra_links) == 0,
        missing_links=[l.target for l in missing_links],
        extra_links=[l.target for l in extra_links],
        total_links=len(original_links),
    )


@weave.op
def validate_headers(original_page: MDPage, translated_page: MDPage, model_output: Any) -> dict:
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
    return dict(
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

    return {"tabs_format_valid": results}


def _validate_technical_words(original_page: MDPage, translated_page: MDPage, dictionary: dict) -> dict:
    """Validate that technical words are translated correctly and maintain their frequency."""
    if not dictionary:
        return {"tech_words_percentage": 1.0, "mismatched": []}
    
    original_word_count = sum(original_page.content.count(re.escape(k)) for k in dictionary)
    translated_word_count = 0
    mismatched = []

    for k, v in dictionary.items():
        original_count = original_page.content.count(re.escape(k))
        translated_count = translated_page.content.count(re.escape(v))
        translated_word_count += translated_count

        if original_count != translated_count:
            mismatched.append((k, v))
    
    tech_words_percentage = translated_word_count / original_word_count if original_word_count > 0 else 1.0
    
    return {
        "tech_words_percentage": tech_words_percentage,
        "mismatched": mismatched
    }

def validate_technical_words(dictionary: dict) -> Callable:
    @weave.op(name="validate_technical_words")
    def _inner(original_page: MDPage, translated_page: MDPage, model_output: Any) -> dict:
        return _validate_technical_words(original_page, translated_page, dictionary)
    return _inner

ALL_SCORERS = [
    validate_links,
    validate_headers,
    validate_tabs,
]

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
    def __init__(self, config: EvalConfig, scorers: list[Callable] = ALL_SCORERS):
        self.config = config
        self.dataset = self.get_dataset()
        self.prompt_template = self._load_prompts()
        self.scorers = self.setup_scorers(scorers)
        self.model_args = {
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        self.setup_judge()

    def setup_scorers(self, scorers: list[Callable]):
        dictionary = yaml.safe_load(self.prompt_template.dictionary)
        return scorers + [validate_technical_words(dictionary)]

    def _load_prompts(self):
        config_folder = Path(self.config.config_folder)
        language = self.config.language
        return PromptTemplate.from_folder(config_folder, language)

    def setup_judge(self):
        self.judge = LLMJudge(
            system_prompt=self.prompt_template.system_prompt,
            evaluation_prompt=self.prompt_template.evaluation_prompt,
            model_args=self.model_args,
        )

    def get_dataset(self):
        logging.info(f"Getting dataset: {self.config.eval_dataset}")
        dataset = weave.ref(self.config.eval_dataset).get()

        def deserialize(md_page):
            """md_page is a string of a dictionary"""
            return MDPage.model_validate(json.loads(md_page))

        ds = [
            {
                "original_page": deserialize(row["original_page"]),
                "translated_page": deserialize(row["translated_page"]),
            }
            for row in dataset.rows
        ]
        logging.info(f"Running eval on {len(ds)} pages")
        return ds

    def evaluate(self):
        evaluation = weave.Evaluation(
            dataset=self.dataset,
            scorers=self.scorers,
        )
        asyncio.run(evaluation.evaluate(self.judge))
