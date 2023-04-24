# gpt_translate

This is a tool to translate the language in Markdown files.

> You will need and OpenAI API key to use this tool

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
$ gpt_translate.file README.md README.ja.md
```

to translate a full folder recursively:

```bash
$ gpt_translate.folder --input_folder docs/ --out_folder docs_ja/
```