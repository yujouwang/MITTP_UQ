import os
import shutil
import re
from pathlib import Path
import glob
import numpy as np
import pandas as pd
import logging
logger = logging.getLogger(__name__)

from src.java_manager import JavaUqBepuStageRun
from src.job_manager import EngagingManager
from src.rf_manager import RfManagerBepuRemote

# ======================================================================
#       Helper Functions
# ======================================================================

def optional_path(path_value):
    """Convert optional YAML path values into Path or None."""
    if path_value in (None, False, ''):
        return None
    return Path(path_value)

def prepare_sim(src, dst_folder):
    """ Copy the sim file to the destination folder """

    # get the sim file name
    file_name = src.stem
    # file_name = file_name.split('@')[0]
    shutil.copy(src, dst_folder/f'{file_name}.sim')
    return

def prepare_ils(src, dst_folder):
    """ Copy the sim file to the destination folder """
    # get the sim file name
    shutil.copy(src, dst_folder/f'ils.csv')
    return

def prepare_exe(src, dst_folder):
    """ Copy the exe file to the destination folder """
    if src is None:
        return
    else:
        shutil.copy(src, dst_folder/'py_exe.sh')
        os.system(f'chmod 777 {dst_folder/"py_exe.sh"}')
    return

def parse_the_bepu_input_var_into_dict(bepu_input_file_path, sample_id):
    """ Parse the bepu input csv file and return a dictionary of input variables 
        for a given sample_id 
    """

    # read the bepu input csv file
    df = pd.read_csv(bepu_input_file_path)

    # take the row with the sample_id
    row = df[df['SampleID'] == sample_id]

    # parse the row into a dictionary
    bepu_input_dict = {}
    for col in df.columns:
        if col != 'SampleID':
            bepu_input_dict[col] = str(row.iloc[0][col])
    return bepu_input_dict



# ======================================================================
#       Classes
# ======================================================================


class UqDriver:
    """ A basee class to manage UQ runs"""
    def __init__(self, path_config, rf_manager: RfManagerBepuRemote, job_manager: EngagingManager, java_manager: JavaUqBepuStageRun) -> None:
        # Set up path
        self.root = Path(path_config['root'])
        self.base_sim_filepath = Path(path_config['base_sim_filepath'])
        self.exe_filepath = optional_path(path_config['exe_filepath'])
        self.bepu_input_path = Path(path_config['bepu_input_path'])
        self.ils_filepath = Path(path_config['ils_filepath'])

        # Set up helper classes
        self.job_manager = job_manager
        self.java_manager = java_manager
        self.rf_manager = rf_manager   

        # A dictionary to store the case folder path for each sample_id
        self._case_folders = {}

    def setup(self):
        """ make working directory and check base sim file """
        logger.info("Setting up the working directory")
        self.root.mkdir(parents=True, exist_ok=True)
        assert self.base_sim_filepath.exists()
    
    def copy_config(self, config_path):
        """ Copy the config file to the root folder """
        logger.info("Copying the config file to the root folder")
        shutil.copy(config_path, self.root / 'config.yaml')
        return

    def init_sample_folder(self, sample_id, folder_suffix=None):
        """ 
        Initiate a sample folder for a given sample_id.
        """
        raise NotImplementedError
    
    def prepare_sample_files(self, sample_id):
        raise NotImplementedError

    def run_sample(self, sample_id):
        raise NotImplementedError



class UqDriverStageRun(UqDriver):
    """ A class to manage UQ for stage run """
    def __init__(self, path_config, rf_manager: RfManagerBepuRemote, job_manager: EngagingManager, java_manager: JavaUqBepuStageRun) -> None:
        super().__init__(path_config, rf_manager, job_manager, java_manager)
    
    def init_sample_folder(self, sample_id, folder_suffix=None):
        """ 
        Initiate a sample folder for a given sample_id.
        """
        logger.info(f'Initiating sample folder for {sample_id} - ')

        # Set up the name of the folder and store it in the dictionary
        # If folder_name is given, overwrite the folder name 
        if folder_suffix is not None:
            case_folder = self.root / f'{sample_id}_{folder_suffix}'
            self._case_folders[sample_id] = case_folder
        else: 
            pass

        
        # Init the case folder and make directory
        case_folder = self._case_folders.get(sample_id, self.root /f'{sample_id}')
        case_folder.mkdir(parents=True, exist_ok=True)
        return 

    def prepare_sample_files(self, sample_id):
        """ Prepare the files for a given sample_id.
        """
        # Copy and paste 
        logger.info(f'Preparing sample files for {sample_id} - ')
        case_folder = self._case_folders.get(sample_id, self.root /f'{sample_id}')

        logger.info('Preparing sim file: from src to destination folder with the same name (without @)')
        prepare_sim(src = self.base_sim_filepath, dst_folder = case_folder)

        logger.info('Preparing ils file)')
        prepare_ils(src = self.ils_filepath, dst_folder = case_folder)

        logger.info('Preparing exe file')
        prepare_exe( src = self.exe_filepath, dst_folder = case_folder)

        logger.info('Preparing java file')
        bepu_input_dict  = parse_the_bepu_input_var_into_dict(bepu_input_file_path=self.bepu_input_path, 
                                                              sample_id=sample_id)
        

        logger.info('Preparing java files')
        self.java_manager.prepare_files(bepu_input_dict=bepu_input_dict, dst_folder=case_folder)

        logger.info('Preparing slurm file')
        self.job_manager.prepare_files(dst_folder=case_folder, sample_id=sample_id)

        logger.info('Preparing rf files remotely')
        self.rf_manager.prepare_rf_files_remote(dst_folder=case_folder, bepu_input_dict=bepu_input_dict)

        return
    
    def run_sample(self, sample_id):
        """ Run the sample with the given sample_id. """
        logger.info(f'Running sample {sample_id} - ')
        case_folder = self._case_folders.get(sample_id, self.root /f'{sample_id}')
        os.chdir(case_folder)

        # Run the job
        self.job_manager.run(sample_id=sample_id)

            
