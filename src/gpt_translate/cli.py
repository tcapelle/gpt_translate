import weave
import shlex
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler
import simple_parsing
from dataclasses import dataclass, asdict

from gpt_translate.translate import _translate_file, _translate_files
from gpt_translate.utils import get_md_files, _copy_images
from gpt_translate.configs import setup_parsing


def setup_logging(debug=False, silence_openai=True, weave_project=None):
    """Setup logging"""
    # Initialize weave
    if weave_project:
        weave.init(weave_project)

    # Setup rich logger
    level = "DEBUG" if debug else "INFO"
    logging.basicConfig(
        level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )

    # silence openai logger
    if silence_openai:
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)


def translate_file(args=None):
    logs_args, translation_args, file_args, model_args = setup_parsing(args=args)
    setup_logging(
        logs_args.debug,
        silence_openai=logs_args.silence_openai,
        weave_project=logs_args.weave_project,
    )
    logging.info(
        f"{logs_args.dumps_yaml()}\n{translation_args.dumps_yaml()}\n{file_args.dumps_yaml()}\n{model_args.dumps_yaml()}"
    )
    asyncio.run(
        _translate_file(
            input_file=file_args.input_file,
            out_file=file_args.out_file,
            replace=translation_args.replace,
            language=translation_args.language,
            config_folder=translation_args.config_folder,
            remove_comments=translation_args.remove_comments,
            do_evaluation=translation_args.do_evaluation,
            model_args=asdict(model_args),
            max_chunk_tokens=translation_args.max_chunk_tokens,
        )
    )


def translate_files(args=None):
    logs_args, translation_args, file_args, model_args = setup_parsing(args=args)
    setup_logging(
        logs_args.debug,
        silence_openai=logs_args.silence_openai,
        weave_project=logs_args.weave_project,
    )
    logging.info(
        f"{logs_args.dumps_yaml()}\n{translation_args.dumps_yaml()}\n{file_args.dumps_yaml()}\n{model_args.dumps_yaml()}"
    )
    asyncio.run(
        _translate_files(
            input_files=file_args.input_file,
            input_folder=file_args.input_folder,
            out_folder=file_args.out_folder,
            replace=translation_args.replace,
            language=translation_args.language,
            config_folder=translation_args.config_folder,
            remove_comments=translation_args.remove_comments,
            do_evaluation=translation_args.do_evaluation,
            max_openai_concurrent_calls=translation_args.max_openai_concurrent_calls,
            model_args=asdict(model_args),
            max_chunk_tokens=translation_args.max_chunk_tokens,
        )
    )


def translate_folder(args=None):
    logs_args, translation_args, file_args, model_args = setup_parsing(args=args)
    setup_logging(
        logs_args.debug,
        silence_openai=logs_args.silence_openai,
        weave_project=logs_args.weave_project,
    )
    logging.info(
        f"{logs_args.dumps_yaml()}\n{translation_args.dumps_yaml()}\n{file_args.dumps_yaml()}\n{model_args.dumps_yaml()}"
    )
    input_files = get_md_files(file_args.input_folder)[: file_args.limit]
    asyncio.run(
        _translate_files(
            input_files=input_files,
            input_folder=file_args.input_folder,
            out_folder=file_args.out_folder,
            replace=translation_args.replace,
            language=translation_args.language,
            config_folder=translation_args.config_folder,
            remove_comments=translation_args.remove_comments,
            do_evaluation=translation_args.do_evaluation,
            max_openai_concurrent_calls=translation_args.max_openai_concurrent_calls,
            model_args=asdict(model_args),
            max_chunk_tokens=translation_args.max_chunk_tokens,
        )
    )


@dataclass
class CopyImagesArgs:
    src_path: Path
    dst_path: Path


def copy_images(args=None):
    args = simple_parsing.parse(CopyImagesArgs)
    print(args)
    _copy_images(args.src_path, args.dst_path)
