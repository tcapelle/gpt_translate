# gpt_translate

This is a tool to translate the language in Markdown files.

> You will need and OpenAI API key to use this tool
## Usage

To translate a single file:

```bash
$ gpt_translate.file --input_file README.md --output_file README.ja.md
```

to translate a full folder recursively:

```bash
$ gpt_translate.folder --input_folder docs/ --out_folder docs_ja/
```