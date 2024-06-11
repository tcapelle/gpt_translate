[![PyPI version](https://badge.fury.io/py/gpt_translate.svg)](https://badge.fury.io/py/gpt_translate)

# gpt_translate: Translating MD files with GPT-4
This is a tool to translate the language in Markdown files.

![](assets/screenshot.png)



> You will need and OpenAI API key to use this tool.

## Installation
We have a stable version on PyPi, so you can install it with pip:
```bash
$ pip install gpt-translate
```
or to get latest version from the repo:

```bash
$ cd gpt_translate
$ pip install .
```
## Usage

We use GPT4 by default. You can change this on `configs/model_config.yaml`

> You can add new languages by providing the language translation dictionaries in `configs/language_dicts`

Export your OpenAI API key:

```bash
export OPENAI_API_KEY=aa-proj-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

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
$ gpt_translate.file --help
```

or:

```bash
$ gpt_translate.folder --help
```

## TroubleShooting

If you have any trouble with the installation, you can always pass the `--debug` flag to get more information about what is happening:

```bash
$ gpt_translate.folder docs docs_ja --language ja --debug
```
this will get you a very verbose output (calls to models, inputs and outputs, etc.)
