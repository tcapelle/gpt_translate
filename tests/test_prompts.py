import os
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from gpt_translate.prompts import PromptTemplate, filter_dictionary


def test_filter_dictionary():
    "Test filtering a dictionary based on specific keys"
    # The function takes a query string and dictionary string, not a dictionary object
    
    # Create a dictionary string like the YAML format used in the app
    dictionary_string = """key1: value1
key2: value2
prefix_key1: special_value1
prefix_key2: special_value2
other: other_value"""
    
    # Create query that should match certain keys
    query = "prefix_key1 and prefix_key2 are special"
    
    # Test filtering based on query
    filtered = filter_dictionary(query, dictionary_string)
    assert "prefix_key1: special_value1" in filtered
    assert "prefix_key2: special_value2" in filtered
    assert "key1: value1" not in filtered
    
    # Test with query that has no matches
    filtered = filter_dictionary("nonexistent", dictionary_string)
    assert filtered == ""
    
    # Test with empty dictionary
    filtered = filter_dictionary("any query", "")
    assert filtered == ""


class TestPromptTemplate:
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    def test_from_files(self, mock_exists, mock_file):
        "Test loading prompt template from files"
        # Setup mock data
        mock_file.side_effect = [
            mock_open(read_data="System prompt with {{output_language}} and {{dictionary}}").return_value,
            mock_open(read_data="Human prompt with {{md_chunk}}").return_value,
            mock_open(read_data="term1: translation1\nterm2: translation2").return_value,
            mock_open(read_data="Evaluation prompt with {{original_page}} and {{translated_page}}").return_value
        ]
        
        # Call method
        template = PromptTemplate.from_files(
            system_prompt_file="/fake/path/system_prompt.txt",
            human_prompt_file="/fake/path/human_prompt.txt", 
            dictionary_file="/fake/path/dict.yaml",
            evaluation_prompt_file="/fake/path/evaluation_prompt.txt"
        )
        
        # Check the template was loaded correctly
        assert template.system_prompt == "System prompt with {{output_language}} and {{dictionary}}"
        assert template.human_prompt == "Human prompt with {{md_chunk}}"
        assert template.dictionary == "term1: translation1\nterm2: translation2"
        assert template.evaluation_prompt == "Evaluation prompt with {{original_page}} and {{translated_page}}"
        assert template.language == "dict"  # From the dictionary_file name
        
        # Check file calls were made properly
        assert mock_file.call_count == 4
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.join')
    def test_from_folder(self, mock_path_join, mock_exists, mock_file):
        "Test creating PromptTemplate from a folder"
        # Setup mock data
        mock_file.side_effect = [
            mock_open(read_data="System prompt").return_value,
            mock_open(read_data="Human prompt").return_value,
            mock_open(read_data="term1: translation1\nterm2: translation2").return_value,
            mock_open(read_data="Evaluation prompt").return_value
        ]
        
        # Set up mock os.path.join to return expected paths
        def mock_join_side_effect(*args):
            if args[-1] == "system_prompt.txt":
                return "/fake/configs/system_prompt.txt"
            elif args[-1] == "human_prompt.txt":
                return "/fake/configs/human_prompt.txt"
            elif args[-1] == "language_dicts/test_lang.yaml":
                return "/fake/configs/language_dicts/test_lang.yaml"
            elif args[-1] == "evaluation_prompt.txt":
                return "/fake/configs/evaluation_prompt.txt"
            return "/fake/configs/" + args[-1]
        
        mock_path_join.side_effect = mock_join_side_effect
        
        # Call method
        template = PromptTemplate.from_folder("/fake/configs", "test_lang")
        
        # Verify template was created correctly
        assert template.language == "test_lang"
        assert mock_file.call_count == 4  # Four files should be read
    
    @patch('gpt_translate.prompts.filter_dictionary')
    def test_format(self, mock_filter_dictionary):
        "Test formatting a template with variables"
        # Mock the filter_dictionary function
        mock_filter_dictionary.return_value = "filtered dictionary content"
        
        # Create a template object with the required fields
        template_obj = PromptTemplate(
            system_prompt="Translate to {{output_language}} using this dictionary: {{dictionary}}",
            human_prompt="Translate this: {{md_chunk}}",
            dictionary="term1: translation1\nterm2: translation2",
            language="es",
            evaluation_prompt="Evaluate translation from {{original_page}} to {{translated_page}}"
        )
        
        # Test the format method
        formatted = template_obj.format(md_chunk="Hello world")
        
        # Check result structure
        assert isinstance(formatted, list)
        assert len(formatted) == 2  # System + user message
        
        # Check system message
        system_message = formatted[0]
        assert system_message["role"] == "system"
        assert "Spanish" in system_message["content"]  # es -> Spanish
        assert "filtered dictionary content" in system_message["content"]
        
        # Check user message
        user_message = formatted[1]
        assert user_message["role"] == "user"
        assert "Hello world" in user_message["content"]
        
        # Verify filter_dictionary was called
        mock_filter_dictionary.assert_called_once_with("Hello world", template_obj.dictionary)