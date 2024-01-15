from pathlib import Path

LANGUAGES_DICT = {"es": "Spanish", "ja": "Japanese", "fr": "French", "de": "German"}

def filter_dictionary(query, dictionary):
    "Filter out words from the query that are not in the dictionary"
    dictionary = dictionary.split("\n")
    filtered_dict = []
    for line in dictionary:
        dict_word = line.split(":")[0].lower()
        if dict_word in query.lower():
            filtered_dict.append(line)
    return "\n".join(filtered_dict)


class PromptTemplate:
    def __init__(
            self, 
            system_prompt: str, # contains {output_language}, {dictionary}
            human_prompt: str,  # contains {md_chunk}
            dictionary: str,     # contains dictionary of words and translations
            language: str       # language of the output
            ):

        self.system_prompt = system_prompt 
        self.human_prompt = human_prompt   
        self.dictionary = dictionary
        self.language = language

    @classmethod
    def from_files(cls, system_prompt_file, human_prompt_file, dictionary_file):
        with open(system_prompt_file, "r") as f:
            system_prompt = f.read()
        with open(human_prompt_file, "r") as f:
            human_prompt = f.read()
        with open(dictionary_file, "r") as f:
            dictionary = f.read()
        language = Path(dictionary_file).stem
        return cls(system_prompt, human_prompt, dictionary, language)

    def __str__(self):
        return (f"System Prompt:\n==============\n{self.system_prompt}"
                f"Human Prompt: \n==============\n{self.human_prompt}")
    
    def filter_dictionary(self, query):
        return filter_dictionary(query, self.dictionary)

    def format(self, md_chunk):
        messages=[{"role": "system",
                   "content": self.system_prompt.format(
                          output_language=LANGUAGES_DICT[self.language],
                          dictionary=self.filter_dictionary(md_chunk)
                   ),
                  },
                  {"role": "user",
                   "content": self.human_prompt.format(md_chunk=md_chunk),
                  },]
        return messages