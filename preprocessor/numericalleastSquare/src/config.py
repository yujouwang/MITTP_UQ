import yaml

def read_config_from_yaml(file_path):
    """
    Reads a YAML configuration file and returns the configuration as a dictionary.
    
    :param file_path: Path to the YAML configuration file.
    :return: Dictionary containing the configuration.
    """
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config