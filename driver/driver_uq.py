
from pathlib import Path
import logging
import sys
import time

from src.uq import UqDriver
from src.job_manager import LocalManager, EngagingManager
from src.java_manager import JavaUqBepuStageRun
from src.rf_manager import RfManagerBepuRemote
from src.config import read_config_from_yaml


# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[ logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python driver_uq.py path/to/config.yaml")
        sys.exit(1)
    CONFIG_PATH = sys.argv[1]

    config = read_config_from_yaml(CONFIG_PATH)
    SAMPLE_LIST = config['rf']['sample_list']
    path_config = {
        'root':config['path']['root'],
        'base_sim_filepath':config['path']['base_sim_filepath'],
        'bepu_input_path':config['path']['bepu_input_path'],
        'ils_filepath':config['path']['ils_filepath']
    }

    # Set up job manager
    job_manager = LocalManager(
        slurm_filepath = config['job']['slurm_filepath'],  
        partition=config['job']['partition'],
        time_for_nodes=config['job']['time_for_nodes'],
        n_nodes=config['job']['n_nodes'],
        n_cores=config['job']['n_cores'],
        n_cores_for_computing=config['job']['n_cores_for_computing'],
        interactive_mode = config['job']['interactive_mode'], 
        rerun = config['job']['rerun']
    )

    java_manager = JavaUqBepuStageRun(
        java_filepath = config['java']['java_filepath'],
        java_keywords = config['java']['java_keywords'],
    )

    rf_manager = RfManagerBepuRemote(
        root = config['path']['root'],
        de_folderpath =config['path']['de_folderpath'],
        ils_filepath=config['path']['ils_filepath'],
        target_quantity = config['rf']['target_quantity'],
        k_l0 =config['rf']['k_l0'],
        s_2 = config['rf']['s_2'],
        n_trunc = config['rf']['n_trunc'],
        n_modes = config['rf']['n_modes'],
        save_every_rf = config['rf']['save_every_rf'],
        model_error_on = config['rf']['model_error_on'],
        disc_error_on = config['rf']['disc_error_on']
    )
    uq = UqDriver(
        path_config = path_config,
        rf_manager = rf_manager,
        job_manager = job_manager, 
        java_manager = java_manager

    )

    uq.setup()
    uq.copy_config(CONFIG_PATH)


    for sample_id in SAMPLE_LIST:
        uq.init_sample_folder(sample_id, folder_suffix=None)
        uq.prepare_sample_files(sample_id)
        uq.run_sample(sample_id)