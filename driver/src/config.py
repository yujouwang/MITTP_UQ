import re
import yaml


def read_config_from_yaml(config_file_path):
    with open(config_file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data


def parse_sample_list(value):
    """Parse sample_list from config: list kept as-is, string 'range(...)' converted to range."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        m = re.fullmatch(r'range\((\d+)(?:,\s*(\d+)(?:,\s*(\d+))?)?\)', value.strip())
        if m:
            args = [int(x) for x in m.groups() if x is not None]
            return range(*args)
    raise ValueError(f"Cannot parse sample_list: {value!r}. Expected a list or 'range(...)'.")
