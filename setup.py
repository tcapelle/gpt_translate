from setuptools import setup, find_packages

exec(open("gpt_translate/version.py").read())

setup(
    name="gpt_translate",
    packages=find_packages(),
    version=__version__,
    license="MIT",
    description="A tool to translate markdown files using GPT-X",
    author="Thomas Capelle",
    author_email="tcapelle@pm.me",
    url="https://github.com/tcapelle/gpt_translate",
    long_description_content_type="text/markdown",
    keywords=[
        "artificial intelligence",
        "generative models",
        "natural language processing",
        "openai",
    ],
    install_requires=["rich", "openai", "fastcore", "langchain", "wandb"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
    ],
    entry_points={
        "console_scripts": [
            "gpt_translate.file=gpt_translate.translate:translate_file",
            "gpt_translate.folder=gpt_translate.translate:translate_folder",
            "gpt_translate.delete_empty_files=gpt_translate.utils:delete_empty_files",
        ]
    },
)
