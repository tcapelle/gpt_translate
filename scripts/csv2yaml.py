from dataclasses import dataclass

import yaml
import simple_parsing
import pandas as pd


@dataclass
class Args:
    file_path: str
    output_path: str = "output.yaml"
    en_columns: int = 0
    language_column: int = 1


if __name__ == "__main__":
    args: Args = simple_parsing.parse(Args)

    df = pd.read_csv(args.file_path)
    columns = df.columns

    df = df.iloc[:, [args.en_columns, args.language_column]]

    # sort by column
    df = df.sort_values(by=columns[args.en_columns])

    data_dict = {
        row[columns[args.en_columns]]: row[columns[args.language_column]]
        for i, row in df.iterrows()
    }

    # Convert the dictionary to a YAML string, allowing Unicode characters
    yaml_str = yaml.dump(data_dict, allow_unicode=True, default_flow_style=False)

    # Print the YAML string to see the output
    print(yaml_str[0:300])

    # To save the YAML string to a file with UTF-8 encoding
    with open(args.output_path, "w", encoding="utf-8") as file:
        yaml.dump(data_dict, file, allow_unicode=True, default_flow_style=False)
