[![PyPI version](https://badge.fury.io/py/termgpt.svg)](https://badge.fury.io/py/gpt_translate)

# gpt_translate


This is a tool to translate the language in Markdown files.

> You will need and OpenAI API key to use this tool.

## Installation
You have to clone the repo and then do:

```bash
$ cd gpt_translate
$ pip install .
```
## Usage

We use GPT4 by default.

To translate a single file:

```bash
$ gpt_translate.file README.md README.jp.md --language jp --model gpt-4
```

to translate a full folder recursively:

```bash
$ gpt_translate.folder --input_folder docs/ --out_folder docs_ja/
```
If you don't know what to do, you can always do:

```bash
$ gpt_translate.folder --help
usage: gpt_translate.folder [-h] [--docs_folder DOCS_FOLDER] [--out_folder OUT_FOLDER] [--replace]
                            [--language LANGUAGE] [--model MODEL] [--verbose]

Translate a folder to Japanese using GPT-3/4

options:
  -h, --help                 show this help message and exit
  --docs_folder DOCS_FOLDER  Folder containing markdown files to translate (default: docs)
  --out_folder OUT_FOLDER    Folder to save the translated files to (default: docs_jpn)
  --replace                  Replace existing files (default: False)
  --language LANGUAGE        Language to translate to (default: jn)
  --model MODEL              Model to use (default: gpt-4)
  --verbose                  Print the output (default: False)
```
## Some notes about the translation

- We use roles defined in [gpt_translate/roles.py](gpt_translate/roles.py) to translate the text. This steers the translation to be more natural. We also give a dictionary of words to translate to the model per translation language. This helps the model translate as we want it to.
- Currently OpenAI API is very slow and tends to timeout on long request. This is way we are splitting the long files in `chunks` of a certain amount of lines. It is a little bit tricky and I am requesting a minimum amount of 40 lines and breaking at headers or double blank spaces. This is not perfect but it works for now.
- As soon as we start translating a file, we create a placeholder translation file. This is to avoid translating the same file twice. If you want to translate a file again, you have to delete the placeholder file or pass the flag `--replace`.
- We are using the `gpt-4` model by default. This is the most powerful model but it is also the slowest. Even if it has a context of 8k tokens, I have not been able to fill this context. I am limiting the context to 2k tokens. This is still a lot of text but it is not enough to translate a whole file. This is why we are splitting the files in chunks. 
> We expect that this issues will be sorted out in the future by OpenAI. 

## Dev

You can run the tests with:

```bash
$ pytest .
```