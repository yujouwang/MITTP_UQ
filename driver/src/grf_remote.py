import json
import csv
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy import special
from scipy.spatial import distance_matrix

import logging
logger = logging.getLogger(__name__)


def _normalized_column_name(column):
    return column.strip().lower()


def find_coordinate_columns(df):
    coord_columns = {}
    for axis in ('x', 'y', 'z'):
        matches = [
            column for column in df.columns
            if _normalized_column_name(column) == axis
            or _normalized_column_name(column).startswith(f'{axis} (')
        ]
        if not matches:
            raise KeyError(
                f"Could not find coordinate column for '{axis.upper()}'. "
                f"Expected labels like '{axis.upper()} (m)', "
                f"'{axis.upper()} (in)', '{axis.upper()}', or '{axis}'. "
                f"Available columns: {list(df.columns)}"
            )
        coord_columns[axis] = matches[0]
    return [coord_columns[axis] for axis in ('x', 'y', 'z')]


class MultiplierBepu:
    def __init__(self, target_quantity, k_l0, s_2, ils_filepath, de_filepath, bepu_input_dict, save_to, model_error_on, disc_error_on):
        self.k_l0 = k_l0
        self.s_2 = s_2
        self.ils_filepath = Path(ils_filepath)
        if de_filepath:
            self.de_filepath = Path(de_filepath)
        else:
            self.de_filepath = None
        self.target_quantity = target_quantity
        self.bepu_input_dict = bepu_input_dict
        self.save_to = Path(save_to)
        self.save_to.mkdir(parents=True, exist_ok=True)

        self.filepaths = {
            'cov_matrix': self.save_to/'cov_matrix.csv',
            'V': self.save_to/'V.csv',
            'D': self.save_to/'D.csv',
        }

        self.ils_me = None
        self.ils_de = None
        self.ils_ie = None
        self.ils_base, self.coord, self.coord_columns = self.init_ils()
        self.model_error_on = model_error_on
        self.disc_error_on = disc_error_on

    def init_ils(self) :
        # Read data
        logger.debug('Get ils: Reading data')
        ils_df = pd.read_csv(self.ils_filepath)
        coord_columns = find_coordinate_columns(ils_df)
        ils_df.sort_values(by=coord_columns, inplace=True, ignore_index=True)
        coord = ils_df[coord_columns].to_numpy()
        ils_base = ils_df[self.target_quantity].to_numpy()
        return ils_base, coord, coord_columns

    def compute_ils_me(self):
        """
        ILS for model error
        """
        logger.debug('Compute model error of ILS')
        if self.model_error_on:
            self.ils_me =  self.ils_base  # example: 10% of the base ILS
        else:
            print(f'Model error off')
            self.ils_me = np.zeros_like(self.ils_base)
        return


    def compute_ils_de(self, rv):
        if self.disc_error_on:
            logger.info('Compute random ils of DE')
            assert self.de_filepath.exists(), f'{self.de_filepath} not found.'
            
            # # Get bounds and compute random ILS values with given uncertainty type
            # bounds = np.loadtxt(self.de_filepath, delimiter=',')
            # lb = bounds[:, 0]
            # ub = bounds[:, 1]

            df = pd.read_csv(self.de_filepath)
            coord_columns = find_coordinate_columns(df)
            df.sort_values(by=coord_columns, inplace=True, ignore_index=True)
            lb = df['LB'].values
            ub = df['UB'].values

            if rv > 0:
                ils_rand = + rv/2 * (self.ils_base - ub)
            else:
                ils_rand = + abs(rv)/2 * (self.ils_base - lb)
                
            ils_rand[ils_rand < 0] = 0  # remove negative values
            self.ils_de = ils_rand
        else:
            print(f'Discretization error off')
            self.ils_de = np.zeros_like(self.ils_base) 
        return

    def compute_ils_ie(self):
        """ ILS for input error """
        self.ils_ie = 0
        return 

    def get_cov_matrix(self):
        logger.debug('Covariance matrix not found. Running process_cov_matrix')
        ils =  self.ils_me + self.ils_de + self.ils_ie
        coord = self.coord

        n = coord.shape[0]
        r  = distance_matrix(coord, coord, p=2)
        ils_mean = np.add.outer(ils, ils) / 2

        # avoid division by zero: 
        ils_mean[ils_mean<1E-9] = 1E-9


        r_l0 = r / (self.k_l0*ils_mean)*2
        g = scipy.special.gamma(1)

        C = np.zeros((n, n))
        C = self.s_2/ g * np.sqrt(2) * r_l0 * scipy.special.kn(1, np.sqrt(2) * r_l0)
        c = self.s_2 / g* np.sqrt(2)
        np.fill_diagonal(C, c)
        np.savetxt(self.filepaths['cov_matrix'], C, delimiter=",")
        return C
 

    def get_de_rv(self):
        de_rv =  self.bepu_input_dict['DEVAR']
        logger.debug(f'de_rv value: {de_rv}')
        return float(de_rv)
    
    def get_xi_coeffs(self, n_truncate):
        return np.array([float(self.bepu_input_dict[f'XI_{i}']) for i in range(n_truncate)])  # minus DEVAR

    
    def get_kle(self, N_truncate):
        logger.info(f'Get KLE')

        # update ils
        self.compute_ils_me()
        de_rv = self.get_de_rv()
        self.compute_ils_de(rv=de_rv)
        self.compute_ils_ie()

        # Compute the grf 
        C = self.get_cov_matrix()
        n_modes = len(C)
        V, D, flags = np.linalg.svd(C)

        # Compose rf
        mu = np.zeros((n_modes,1))
        xi_coeffs = self.get_xi_coeffs(N_truncate)
        rf = mu + V[:, :N_truncate] @ (np.diag(np.sqrt(D[:N_truncate])) @xi_coeffs.reshape(-1, 1))
        rf_lognormal = np.exp(np.sqrt(self.s_2)*rf)
        logger.info('Finished generating random field using KLE')

        # Create data framew 
        coord = self.coord
        # Save V and D
        np.savetxt(self.filepaths['V'], V, delimiter=",")
        np.savetxt(self.filepaths['D'], D, delimiter=",")

        # df 
        df = pd.DataFrame(np.concatenate([coord, rf_lognormal], axis=1), columns=[*self.coord_columns, 'phi'])
        return df

    def df(self, N_trunc):
        # read data
        filepath = self.filepaths.get(f'rf_trunc{N_trunc}', self.save_to/f'rf_trunc{N_trunc}.csv')
        if filepath.exists() is False:
            raise FileNotFoundError(f'{filepath} not found.')
        else:
            df = pd.read_csv(filepath)
        return df
    
    
    def get_sample(self, N_trunc, sample_id):
        return self.df(N_trunc).iloc[:, sample_id+4].to_numpy()


def write_rf_csv(df, filepath):
    with open(filepath, 'w', newline='') as f:
        header = [f'"{column}"' if column in df.columns[:3] else column for column in df.columns]
        f.write(','.join(header) + '\n')
        df.to_csv(f, index=False, header=False, quoting=csv.QUOTE_MINIMAL)


def read_config(config_path):
    """ Read the config file """
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


if __name__ == "__main__":

    current_dir = Path(__file__).parent
    config_path = current_dir / 'rf_dict.json'
    bepu_path = current_dir / 'bepu_input_dict.json'
    ils_filepath = current_dir / 'ils.csv'

    var_config = read_config(config_path = config_path)
    target_quantity = var_config['target_quantity']
    k_l0 = float(var_config['k_l0'])
    s_2 = float(var_config['s_2'])
    de_filepath = var_config['de_filepath']
    n_trunc = int(var_config['n_trunc'])

    bepu_input_dict = read_config(bepu_path)

    # Initialize the variables
    m = MultiplierBepu(
        target_quantity = target_quantity,
        k_l0 = k_l0, 
        s_2 = s_2, 
        ils_filepath=ils_filepath, 
        de_filepath = de_filepath,
        bepu_input_dict=bepu_input_dict, 
        model_error_on = var_config['model_error_on'],
        disc_error_on = var_config['disc_error_on'],
        save_to='.')

    # m.get_cov_matrix()
    df = m.get_kle(N_truncate=n_trunc)

    # Dump the phi as rf.csv
    write_rf_csv(df, 'rf.csv')
