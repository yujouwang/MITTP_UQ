import shutil
import os
from pathlib import Path
import logging
# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[ logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

from src.config import read_config_from_yaml
from src.ls import GridInfo, FieldLS


CONFIG_PATH = './config/tall3D_ss_BOT.yaml'


def create_ls_field(config):

    # Create the grid information from the config
    grid_info_list = []
    for grid in config['grids'].values():
        grid_info_list.append(
            GridInfo(
                grid['name'],
                Path(grid['dir']),
                int(grid['N']),
                float(grid['V']),
                Path(grid['field_file_name'])
            )
        )

    # Create the field ls object
    field = FieldLS(
        grid_info_list=grid_info_list,
        field_name = config['ls']['field_name'],
        save_ls_to = Path(config['ls']['save_to'])
    )
    return field


if __name__ == "__main__":

    # Read the config file
    config = read_config_from_yaml(CONFIG_PATH)
    print(f"Config: {config}")

    # Create the save directory if it does not exist
    save_dir = Path(config['ls']['save_to'])
    save_dir.mkdir(parents=True, exist_ok=True)

    # Create the LS field 
    logging.info("Creating least-square field...")
    field = create_ls_field(config)

    # Read the data 
    logging.info("Collecting data for the field...")
    field.collect_data()

    # Compute
    logging.info("Starting field  computation...")
    points_idx = range(int(config['points']['start']), int(config['points']['end']))
    field.compute_field_ls(parallel=True, points_idx=points_idx)
    logging.info("Field computation completed.")

    # Compute the bounds
    field.read_field_ls()
    for i in range(len(field.grid_info_list)):
        field.compute_bounds(grid_id=i)





    
