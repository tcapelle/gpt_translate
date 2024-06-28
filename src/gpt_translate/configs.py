import shlex
import logging
from dataclasses import dataclass
import simple_parsing
from simple_parsing.helpers import Serializable

DEFAULT_CONFIG_PATH = "./configs_dev/config.yaml"


# This file is in sync with the config.yaml file


@dataclass
class ModelConfig(Serializable):
    model: str = "gpt-4o"  # Model to use
    temperature: float = 1.0  # Temperature to use


@dataclass
class LogsConfig(Serializable):
    debug: bool = False  # Debug mode
    weave_project: str = None  # Weave project
    silence_openai: bool = True  # Silence OpenAI logger


@dataclass
class TranslationConfig(Serializable):
    language: str = "es"  # Language to translate to
    config_folder: str = "./configs"  # Config folder
    replace: bool = False  # Replace existing file
    remove_comments: bool = True  # Remove comments
    do_evaluation: bool = True  # Do evaluation
    max_openai_concurrent_calls: int = 7  # Max number of concurrent calls to OpenAI
    max_chunk_tokens: int = 3600  # Max number of tokens in a chunk


@dataclass
class FilesConfig(Serializable):
    input_file: str = (
        "docs/intro.md"  # File to translate, can be a .txt file with a list of files when sued with translate.files
    )
    out_file: str = "intro_ja.md"  # File to save the translated file to
    input_folder: str = None  # Folder to translate
    out_folder: str = None  # Folder to save the translated files to
    limit: int = None  # Limit number of files to translate


def setup_parsing(args):
    parser = simple_parsing.ArgumentParser(
        config_path=DEFAULT_CONFIG_PATH, add_config_path_arg=True
    )
    parser.add_arguments(LogsConfig, dest="logs")
    parser.add_arguments(TranslationConfig, dest="translation")
    parser.add_arguments(FilesConfig, dest="files")
    parser.add_arguments(ModelConfig, dest="model")

    if isinstance(args, str):
        args = shlex.split(args)
    args = parser.parse_args(args)
    logs_args: LogsConfig = args.logs
    translation_args: TranslationConfig = args.translation
    file_args: FilesConfig = args.files
    model_args: ModelConfig = args.model

    return logs_args, translation_args, file_args, model_args
