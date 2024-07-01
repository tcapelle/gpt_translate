from setuptools import setup

exec(open("src/gpt_translate/version.py").read())

setup(
    version=__version__,
)
