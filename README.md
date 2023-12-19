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

We use GPT4 by default. You can change this on `configs/model_config.yaml`

> You can add new languages by providing the language translation dictionaries in `configs/language_dicts`


To translate a single file:

```bash
$ gpt_translate.file README.md README_es_.md --language es
```

to translate a full folder recursively:

```bash
$ gpt_translate.folder docs docs_ja --language ja
```

If you don't know what to do, you can always do:

```bash
$ gpt_translate --help
```
