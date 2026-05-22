"""This module performs Latin Hypercube Sampling (LHS) to generate samples for uncertain parameters."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
import yaml


DEFAULT_N_SAMPLES = 59


def lhs_gaussian_independent(mu_dict, sigma_dict, N, seed=None):
    """
    mu, sigma: dict
    return: dict 
    """
    rng = np.random.default_rng(seed)
    d = len(mu_dict)

    X = {}

    for key in mu_dict.keys():
        u = (np.arange(N) + rng.random(N)) / N
        rng.shuffle(u)

        if 'XI' in key or key == 'DEVAR':
            #  standard normal
            X[key] = norm.ppf(u)
        else:

            if type(mu_dict[key]) == tuple:
                for j in range(len(mu_dict[key])):
                    X[f'{key}_{j+1}'] = mu_dict[key][j] + sigma_dict[key] * norm.ppf(u)
            else:
                X[key] = mu_dict[key] + sigma_dict[key] * norm.ppf(u)

    return X


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate BEPU LHS samples using a YAML config file."
    )
    parser.add_argument(
        "config_path",
        type=Path,
        help="Path to the YAML config file, e.g. files/input_error/input_error_config.yaml",
    )
    return parser.parse_args()


def read_config_from_yaml(config_path):
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


def parse_input_error(config):
    input_error = config.get("input_error")

    # PyYAML reads the plain YAML value `None` as a string, while `null`
    # becomes Python None. Accept both as "no input-error variables".
    if input_error is None or (
        isinstance(input_error, str) and input_error.strip().lower() in {"none", "null"}
    ):
        return {}, {}
    if not isinstance(input_error, dict):
        raise ValueError("input_error must be a mapping or None.")

    mu = {}
    sigma = {}
    for name, values in input_error.items():
        if not isinstance(values, dict):
            raise ValueError(f"input_error.{name} must contain 'mean' and 'std'.")
        if "mean" not in values or "std" not in values:
            raise ValueError(f"input_error.{name} must contain both 'mean' and 'std'.")

        mu[name] = values["mean"]
        sigma[name] = values["std"]

    return mu, sigma


def get_save_path(config):
    try:
        return Path(config["path"]["save_to"])
    except KeyError as exc:
        raise ValueError("Config must define path.save_to.") from exc


def get_n_modes(config):
    try:
        return int(config["model_error"]["N_modes"])
    except KeyError as exc:
        raise ValueError("Config must define model_error.N_modes.") from exc


def main(mu, sigma, n_modes, save_to):
    # Add input variables: discretization error rv
    mu[f'DEVAR'] = 0.0
    sigma[f'DEVAR'] = 1.0

    # Add input variables: mode coefficients
    for mode in range(n_modes):
        mu[f'XI_{mode}'] = 0.0
        sigma[f'XI_{mode}'] = 1.0
    
    print('Mean values:', mu)
    print('Std values:', sigma)

    # get samples 
    print('Generating LHS samples...')
    print(len(list(mu.values())))
    X = lhs_gaussian_independent(mu_dict=mu, sigma_dict=sigma, N=DEFAULT_N_SAMPLES, seed=42)


    # create DataFrame
    df = pd.DataFrame(X)

    # Add the first column as SampleID
    df.insert(0, 'SampleID', range(len(df)))


    save_to.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(save_to, index=False)
    print(f'Saved LHS samples to {save_to}')
    return


if __name__ == "__main__":
    args = parse_args()
    config = read_config_from_yaml(args.config_path)
    save_to = get_save_path(config)
    n_modes = get_n_modes(config)
    mu, sigma = parse_input_error(config)

    if save_to.exists():
        raise FileExistsError(f'{save_to} already exists! Delete it first to proceed.')

    else:
        main(mu, sigma, n_modes, save_to)
