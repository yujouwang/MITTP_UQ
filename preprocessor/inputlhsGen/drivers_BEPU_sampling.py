"""This module performs Latin Hypercube Sampling (LHS) to generate samples for uncertain parameters"""

import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.stats import norm

from pathlib import Path


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


# =========================================================
#               Data 
# =========================================================
# BOT
sigma_bot = {
    'MASSFLOW': 0.02/2, 
    'TIN': 2/2, 
    'POWERIN':202.64/2,
    'RHO_LBE': 85.8/2,
    'Cp_LBE': 8.274/2,
    'K_LBE': 1.101/2,
    'MU_LBE': 0.00003592/2,
}

mu_bot = {
    'MASSFLOW':1.3096,
    'TIN': 508.56,
    'POWERIN': 4052.83,
    'RHO_LBE': 10725.0,
    'Cp_LBE': 118.2,
    'K_LBE': 7.34,
    'MU_LBE': 0.000449
}

def main(mu, sigma):
    """ 
    input: mu and sigma are dictionaries look like this: 

    sigma_eot = {
        'MASSFLOW': 0.05, 
        'TIN': 2, 
        'POWERIN':202.64,
        'RHO_LBE': 85.8,
        'Cp_LBE': 8.274,
        'K_LBE': 1.101,
        'MU_LBE': 0.00003592,
    }

    mu_eot = {
        'MASSFLOW': 0.2644,
        'TIN': 474.95,
        'POWERIN': 4052.83,
        # 'RHO_LBE': (10725.0, -1.22),
        'RHO_LBE': 10725.0,
        # 'Cp_LBE': (118.2, 0.005934, 7183000.0),
        'Cp_LBE': 118.2,
        # 'K_LBE': (7.34, 0.0095),
        'K_LBE': 7.34,
        'MU_LBE': 0.000449
    }

    """
    # Add input variables: discretization error rv
    mu[f'DEVAR'] = 0.0
    sigma[f'DEVAR'] = 1.0

    # Add input variables: mode coefficients
    for mode in range(N_modes):
        mu[f'XI_{mode}'] = 0.0
        sigma[f'XI_{mode}'] = 1.0
    
    print('Mean values:', mu)
    print('Std values:', sigma)

    # get samples 
    print('Generating LHS samples...')
    print(len(list(mu.values())))
    X = lhs_gaussian_independent(mu_dict=mu, sigma_dict=sigma, N=59, seed=42)


    # create DataFrame
    df = pd.DataFrame(X)

    # Add the first column as SampleID
    df.insert(0, 'SampleID', range(len(df)))


    df.to_csv(save_to, index=False)
    print(f'Saved LHS samples to {save_to}')
    return


if __name__ == "__main__":
    # save to CSV
    save_to = Path('../../../files/input_error/BEPU_bot_lhs_samples_r20v4_2sigma.csv')

    # Specify the modes 
    N_modes = 20
    mu = mu_bot.copy()
    sigma = sigma_bot.copy()

    if save_to.exists():
        raise FileExistsError(f'{save_to} already exists! Delete it first to proceed.')

    else:
        main(mu, sigma)
