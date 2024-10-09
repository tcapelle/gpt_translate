# This file is in sync with the config.yaml file

from dataclasses import dataclass
from pathlib import Path
import simple_parsing
from simple_parsing.helpers import Serializable

DEFAULT_CONFIG_PATH = "./configs/config.yaml"
DEFAULT_EVAL_CONFIG_PATH = "./configs/eval_config.yaml"


@dataclass
class TranslateConfig(Serializable):
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
    do_translate_header_description: bool  # Translate the header description
    max_openai_concurrent_calls: int  # Max number of concurrent calls to OpenAI

    input_file: str  # File to translate, can be a .txt file with a list of files when used with translate.files
    out_file: str  # File to save the translated file to
    input_folder: str = "./docs/"  # Folder to translate
    out_folder: str = "./docs_translated/"  # Folder to save the translated files to
    limit: int = None  # Limit number of files to translate

@dataclass
class EvalConfig(Serializable):
    model: str  # Model to use
    temperature: float  # Temperature to use
    max_tokens: int  # Max tokens to use

    debug: bool  # Debug mode
    weave_project: str  # Weave project
    silence_openai: bool  # Silence OpenAI logger

    language: str  # Language to translate to
    config_folder: str  # Config folder
    max_openai_concurrent_calls: int  # Max number of concurrent calls to OpenAI

    eval_dataset: str = "Translation-ja:latest"  # the Weave dataset name to evaluate

@dataclass
class CopyImagesArgs:
    src_path: Path
    dst_path: Path

@dataclass
class NewFilesArgs:
    repo: Path
    extension: str = ".md"
    since_days: int = 14
    out_file: Path = "./changed_files.txt"


def setup_parsing(args=None, config_class=TranslateConfig, config_path=DEFAULT_CONFIG_PATH):
    config = simple_parsing.parse(
        config_class=config_class,
        config_path=config_path,
        args=args,
        add_config_path_arg=True,
    )
    return config
