import json
import os 
from pathlib import Path
import shutil
import logging
logger = logging.getLogger(__name__)


# ========================================================
#              RfManager Classes
# ========================================================

class RfManagerBepuRemote:
    def __init__(self, root, py_filepath, de_folderpath, ils_filepath, target_quantity, k_l0, s_2, n_trunc, n_modes, save_every_rf, model_error_on, disc_error_on):
        self.root = Path(root)
        self.py_filepath = Path(py_filepath)
        if de_folderpath:
            self.de_folderpath = Path(de_folderpath)
        else:
            self.de_folderpath = None

        self.ils_filepath = Path(ils_filepath)
        self.target_quantity = target_quantity
        self.k_l0 = k_l0
        self.s_2 = s_2
        self.n_trunc = n_trunc
        self.n_modes = n_modes
        self.save_every_rf = save_every_rf
        self.model_error_on = model_error_on
        self.disc_error_on = disc_error_on

        if self.disc_error_on:
            assert self.de_folderpath.exists()

    def prepare_rf_files_remote(self, dst_folder, bepu_input_dict):
        # copy the rf generation script
        dst = dst_folder / 'grf.py'
        shutil.copy(self.py_filepath, dst)

        # Create a dictionary file 
        de_filepath = (self.de_folderpath / 'U.csv') 
        rf_dict = {
            'target_quantity': self.target_quantity,
            'k_l0': self.k_l0,
            's_2': self.s_2,
            'n_trunc': self.n_trunc,
            'de_filepath': str(de_filepath),
            'model_error_on': self.model_error_on,
            'disc_error_on':self.disc_error_on
        }

        # save the dict as a json file
        rf_dict_filepath = dst_folder/'rf_dict.json'
        with open(rf_dict_filepath, 'w') as f:
            json.dump(rf_dict, f, indent=4)

    
        # save the bepu_input_dict
        bepu_input_dict_filepath = dst_folder/'bepu_input_dict.json'
        with open(bepu_input_dict_filepath, 'w') as f:
            json.dump(bepu_input_dict, f, indent=4)
        return

    def generate_rf(self, dst_folder):
        python_path = dst_folder / 'grf.py'
        logging.info(f'Launching rf generation script: {python_path}')
        os.system(f'python {python_path} ')
        return
