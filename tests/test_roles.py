from gpt_translate.roles import filter_dictionary, DICTIONARIES

ES_DICT = DICTIONARIES["es"]

def test_filter_dictionary():
    en_text = """
    This text is in English. It has some words that are not in the dictionary.
    For example we have Artifact, API key, and Bayesian search.
    Other Weights and biases words like: server, client, and architecture.
    """

    fdict = filter_dictionary(en_text, ES_DICT)
    print(fdict)