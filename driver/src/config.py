import yaml


def read_config_from_yaml(config_file_path): 
    with open(config_file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data
