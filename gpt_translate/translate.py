from pathlib import Path
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential, # for exponential backoff
)

from gpt_translate.prompts import PromptTemplate
from gpt_translate.loader import remove_markdown_comments, split_markdown
from gpt_translate.utils import count_tokens

client = OpenAI()

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)

def translate_chunk(chunk:str, prompt:PromptTemplate):
    """Translate a markdown chunk
    chunk: markdown chunk
    prompt: PromptTemplate object
    return: translated chunk
    """
    res = completion_with_backoff(
        model="gpt-4", 
        messages=prompt.format(md_chunk=chunk))

    return res.choices[0].message.content

def translate_splitted_md(
        splitted_markdown:list[str], 
        prompt:PromptTemplate, 
        max_chunk_tokens:int=400, 
        sep:str="\n\n")->str:
    """Translate a list of markdown chunks
    splitted_markdown: list of markdown chunks
    prompt: PromptTemplate object
    max_chunk_tokens: maximum number of tokens per chunk
    sep: separator between chunks
    return: translated markdown file
    """

    packed_chunks = ""
    translated_file = ""
    packed_chunks_len = 0

    for i, chunk in enumerate(splitted_markdown):
        
        n_tokens = count_tokens(chunk)

        if packed_chunks_len + n_tokens <= max_chunk_tokens:
            print(f"Packing chunk {i} with {n_tokens} tokens")
            packed_chunks += sep + chunk
            packed_chunks_len += n_tokens
        else:
            print(f">> Translating {packed_chunks_len} tokens")
            t_chunk = translate_chunk(packed_chunks, prompt)
            translated_file += sep + t_chunk
            print(f"Packing chunk {i} with {n_tokens} tokens")
            packed_chunks = chunk
            packed_chunks_len = n_tokens

    return translated_file
class Translator:
    "A class to translate markdown files"
    def __init__(self, config_folder, language="ja", max_chunk_tokens:int=400):
        self.config_folder = Path(config_folder)
        self.language = language
        self.prompt_template = PromptTemplate.from_files(
            self.config_folder / "system_prompt.txt",
            self.config_folder / "human_prompt.txt",
            self.config_folder / f"language_dicts/{language}.yaml"
        )
        self.max_chunk_tokens = max_chunk_tokens
    
    def translate_file(self, md_file:str, remove_comments:bool=True):
        """Translate a markdown file"""
        with open(md_file, "r") as f:
            md_content = f.read()
        if remove_comments:
            md_content = remove_markdown_comments(md_content)
        chunks = split_markdown(md_content)
        translated_file = translate_splitted_md(chunks,
                                                self.prompt_template,
                                                max_chunk_tokens=self.max_chunk_tokens)
        return translated_file