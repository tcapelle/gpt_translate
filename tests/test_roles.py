from textwrap import dedent
from gpt_translate.prompts import filter_dictionary, DICTIONARIES

ES_DICT = DICTIONARIES["es"]


def test_filter_dictionary():
    en_text = """
    This text is in English. It has some words that are not in the dictionary.
    For example we have Artifact, API key, and Bayesian search.
    Other Weights and biases words like: server, client, and architecture.
    """

    fdict = filter_dictionary(en_text, ES_DICT)
    test_fdict = dedent(
        """\
        API key: clave API
        artifact: artefacto
        Bayesian search: búsqueda bayesiana
        bias: sesgo
        key: clave
        server: servidor
        """
    )
    assert fdict == test_fdict
