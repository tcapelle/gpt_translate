This fork of `gpt_translate` includes the config files (mainly glossary) for translating the [StarRocks docs](https://docs.starrocks.io) from English into Chinese.

Please submit a PR to the parent of this fork at [`tcapelle/gpt_translate`](https://github.com/tcapelle/gpt_translate) if you change any files other than:
- this README
- `config/**`

Use at StarRocks:

1. Export the GPT `OPENAI_API_KEY`

  ```bash
  export OPENAI_API_KEY=sk-proj-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
  ```

2. Translate a file

> Tip
>
> The first time that you run the command you will be asked to paste a credential from your Weights \& Biases account. Sign up and create the account. The Weave feature from W\&B is useful for understanding the impact of changes you make to the translation workflow.
>
> The API key will be available at https://wandb.ai/authorize after you create the account.

- Clone this repo and change dir into it
- Install gpt_translate
  ```bash
  pip install .
  ```
- Translate a file. For example, to translate the Helm Quick Start:

  ```bash
  gpt_translate.file \
    --input_file ~/GitHub/starrocks/docs/en/quick_start/helm.md \
    --out_file docs/helm.md \
    --language zh
  ```
> Note
>
> You can pass in the config dir, input and output folders, etc. See the output of `gpt_translate.file -h`. I am only documenting how I personally use this during testing, and I run the command from the directory where I cloned my fork.

## Tuning

Most (probably all) of the changes that you make will be in the `config/` dir:

```bash
config.yaml
human_prompt.txt
system_prompt.txt
evaluation_prompt.txt
configs/language_dicts/zh.yaml
```

### `config.yaml`

The main change that I made to `config.yaml` was to `temperature`. I set this to `0.2` to reduce the "creativity" of GPT. This should increase the probability that our docs will be translated in the same way every time. In reviews of the output, the "tone" of the translated test docs improved with lower `temperature`.

### `human_prompt.txt`

`human_prompt.txt` contains a list of terms that should never be translated from English. If you notice terms that should be left in English, add them here.

For example:

```bash
- StarRocks
- external catalog
- tablet
```

### `system_prompt.txt`

This is the main instruction file for GPT, it includes most of the "prompt". I modified the default prompt from W\&B to instruct GPT to leave the code blocks alone (by default comments in code blocks were being translated). We should discuss how we want to deal with comments in code blocks, maybe they should be translated?

Additionally, I added a prompt that follows the AWS "Evidence-Based Narrative" writing guide. I am hoping that this will reduce the inclusion of marketing fluff.

### `evaluation_prompt.txt`

This is an interesting file, after the translation is complete the translation is evaluated and the results are presented in the W\&B page.

### `zh.yaml`

This is our glossary. If you would like to change how a phrase is translated from English to Chinese please add an entry.

Examples:

```yaml
FEs: FE
BEs: BE
Data loading: 数据导入
Data unloading: 数据导出
load: 导入
native table: 内表
Cloud-native table: 存算分离表
```

## Original README:

[![PyPI version](https://badge.fury.io/py/gpt_translate.svg)](https://badge.fury.io/py/gpt_translate)
[![Weave](https://raw.githubusercontent.com/wandb/weave/master/docs/static/img/logo.svg)](https://wandb.ai/capecape/gpt-translate/weave/)

# gpt_translate: Translating MD files with GPT-4
This is a tool to translate Markdown files without breaking the structure of the document. It is powered by OpenAI models and has multiple parsing and formatting options. The provided default example is the one we use to translate our documentation website [docs.wandb.ai](https://docs.wandb.ai) to [japanese](https://docs.wandb.ai/ja/) and [korean](https://docs.wandb.ai/ko/).

![](assets/screenshot.png)

> You can click [here](https://wandb.ai/capecape/gpt-translate/r/call/a18deff9-a963-4ad6-b5d6-b0ae63580575) to see the output of the translation on the screenshot above.

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

Export your OpenAI API key:

```bash
export OPENAI_API_KEY=aa-proj-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

## Usage

The library provides a set of commands that you can access as CLI. All the commands start by `gpt_translate.`:

- `gpt_translate.file`: Translate a single file
- `gpt_translate.folder`: Translate a folder recursively
- `gpt_translate.files`: Translate a list of files, accepts `.txt` list of files as input.

Export your OpenAI API key:

```bash
export OPENAI_API_KEY=aa-proj-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

We use GPT4 by default. You can change this on `configs/config.yaml`. The dafault values are:

```yaml
# Logs:
debug: false  # Debug mode
weave_project: "gpt-translate"  # Weave project
silence_openai: true  # Silence OpenAI logger

# Translation:
language: "ja"  # Language to translate to
config_folder: "./configs"  # Config folder, where the prompts and dictionaries are
replace: true  # Replace existing file
remove_comments: true  # Remove comments
do_evaluation: true  # Do evaluation
do_translate_header_description: true  # Translate the header description
max_openai_concurrent_calls: 7  # Max number of concurrent calls to OpenAI

# Files:
input_file: "docs/intro.md"  # File to translate
out_file: " intro_ja.md"  # File to save the translated file to
input_folder: null  # Folder to translate
out_folder: null  # Folder to save the translated files to
limit: null  # Limit number of files to translate

# Model:
model: "gpt-4o"
temperature: 1.0
max_tokens: 4096

```
You can override the arguments at runtime or by creating another `config.yaml` file. You can also use the `--config_path` flag to specify a different config file.

- The `--config_folder` argument is where the prompts and dictionaries are located, the actual `config.yaml` could be located somewhere else. Maybe I need a better naming here =P.

- You can add new languages by providing the language translation dictionaries in `configs/language_dicts`

## Examples

1. To translate a single file:

```bash
$ gpt_translate.file \
  --input_file README.md \
  --out_file README_es_.md \
  --language es
```

2. Translate a list of files from `list.txt`:

```bash
$ gpt_translate.files \
  --input_file list.txt \
  --input_folder docs \ 
  --out_folder docs_ja \
  --language ja
```

Note here that we need to pass and input and output folder. This is because we will be using the input folder to get the relative path and create the same folder structure in the output folder. This is tipically what you want for documentation websites that are organized in folders like `./docs`.

3. Translate a full folder recursively:

```bash
$ gpt_translate.folder \
  --input_folder docs \
  --out_folder docs_ja \
  --language ja
$ gpt_translate.file --help
```

If you don't know what to do, you can always do `--help` on any of the commands:

```bash
$ gpt_translate.* --help
```

## Validation

The library performs an evaluation of the quality of the translation if `--do_evaluation` is set to `true`.
You can modify the output of the LLM evaluation by changing the `configs/evaluation_prompt.txt`.

Play with this prompt and maybe you can find better ways to evaluate the quality of the translation.

## Weave Tracing

The library does a lot! keeping track of every piece of interaction is necessary. We added [W&B Weave](wandb.me/weave) support to trace every call to the model and underlying processing bits.

You can pass a project name to the CLI to trace the calls:

```bash
$ gpt_translate.folder \
  --input_folder docs \
  --output_folder docs_ja \
  --language ja \
  --weave_project gpt-translate
```

![Weave Tracing](./assets/weave.png)


## TroubleShooting

If you have any issue, you can always pass the `--debug` flag to get more information about what is happening:

```bash
$ gpt_translate.folder ... --debug
```
this will get you a very verbose output (calls to models, inputs and outputs, etc.)
