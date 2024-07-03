# This file is in sync with the config.yaml file

import shlex
import logging
from dataclasses import dataclass
import simple_parsing
from simple_parsing.helpers import Serializable

DEFAULT_CONFIG_PATH = "./configs/config.yaml"


@dataclass
class Config(Serializable):
    model: str  # Model to use
    temperature: float  # Temperature to use
    max_tokens: int  # Max tokens to use

    debug: bool  # Debug mode
    weave_project: str  # Weave project
    silence_openai: bool  # Silence OpenAI logger

    language: str  # Language to translate to
    config_folder: str  # Config folder
    replace: bool  # Replace existing file
    remove_comments: bool  # Remove comments
    do_evaluation: bool  # Do evaluation
    do_translate_header_description: bool  # Translate the header description
    max_openai_concurrent_calls: int  # Max number of concurrent calls to OpenAI

    input_file: str  # File to translate, can be a .txt file with a list of files when used with translate.files
    out_file: str  # File to save the translated file to
    input_folder: str  # Folder to translate
    out_folder: str  # Folder to save the translated files to
    limit: int = None  # Limit number of files to translate


def setup_parsing(args):
    # parser = simple_parsing.ArgumentParser(
    #     config_path=DEFAULT_CONFIG_PATH, add_config_path_arg=True
    # )
    # parser.add_arguments(LogsConfig, dest="logs")
    # parser.add_arguments(TranslationConfig, dest="translation")
    # parser.add_arguments(FilesConfig, dest="files")
    # parser.add_arguments(ModelConfig, dest="model")

    config = simple_parsing.parse(
        config_path=DEFAULT_CONFIG_PATH,
        config_class=Config,
        args=args,
        add_config_path_arg=True,
    )
    # logs_args: LogsConfig = args.logs
    # translation_args: TranslationConfig = args.translation
    # file_args: FilesConfig = args.files
    # model_args: ModelConfig = args.model
    # return logs_args, translation_args, file_args, model_args
    return config
