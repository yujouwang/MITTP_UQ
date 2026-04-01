import os
from pathlib import Path
import glob
import logging
logger = logging.getLogger(__name__)

class JobManager:
    """ A class to manage the job submission. 
    The class should be inherited and the run method should be implemented.
    Subclasss should implement prepare_files and run methods.
    """
    def __init__(self):
        pass

    def prepare_files(self):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

class LocalManager(JobManager):
    def __init__(self, slurm_filepath, partition, time_for_nodes, n_nodes, n_cores, n_cores_for_computing, 
                 interactive_mode=False, rerun=False, check_file='DONE'):
        logger.info('Initializing LocalManager')
        self.slurm_filepath = Path(slurm_filepath)
        assert self.slurm_filepath.exists()
        self.partition = partition
        self.time_for_nodes = time_for_nodes
        self.n_nodes = n_nodes
        self.n_cores = n_cores
        self.n_cores_for_computing = n_cores_for_computing
        self.interactive_mode = interactive_mode
        self.rerun = rerun
        self.check_file = check_file

        self.slurm_name = {}

    def prepare_files(self, dst_folder, sample_id):
        """ Prepare the files for local run. 
        """
        with open(self.slurm_filepath, 'r', encoding='utf-8') as f:
            content = f.read()


        # Specify the number of cores for computing
        content = content.replace('N_CORES_FOR_COMPUTING', str(self.n_cores_for_computing))

        # Specify the sim file name
        sim_file_name = glob.glob1(dst_folder, '*.sim')[0]
        content = content.replace('SIM_FILE_NAME', sim_file_name)

        # Write the slurm file to the destination folder
        bash_name = f'r_{sample_id}.sh'
        self.slurm_name[sample_id] = bash_name
        dst = dst_folder / bash_name
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(content)
        return 

    def run(self, sample_id):
        """ Run the job for local run. 
            For local run, we can directly run the command in the terminal. 
        """
        cmd = f'chmod 777 {self.slurm_name[sample_id]} && ./{self.slurm_name[sample_id]}'
        os.system(cmd)

        return


class EngagingManager(JobManager):
    def __init__(self, slurm_filepath, partition, time_for_nodes, n_nodes, n_cores, n_cores_for_computing, 
                 interactive_mode=False, rerun=False, check_file='DONE'):
        logger.info('Initializing EngagingManager')
        self.slurm_filepath = Path(slurm_filepath)
        assert self.slurm_filepath.exists()
        self.partition = partition
        self.time_for_nodes = time_for_nodes
        self.n_nodes = n_nodes
        self.n_cores = n_cores
        self.n_cores_for_computing = n_cores_for_computing
        self.interactive_mode = interactive_mode
        self.rerun = rerun
        self.check_file = check_file

        self.slurm_name = {}
    
    def prepare_files(self, dst_folder, sample_id):
        """ Prepare slurm for Engaging """

        with open(self.slurm_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Specify the number of cores for computing
        content = content.replace('N_CORES_FOR_COMPUTING', str(self.n_cores_for_computing))

        # Specify the sim file name
        sim_file_name = glob.glob1(dst_folder, '*.sim')[0]
        content = content.replace('SIM_FILE_NAME', sim_file_name)

        # Specify the java name
        java_name = glob.glob1(dst_folder, '*.java')[0]
        java_name = java_name.split('.')[0]
        print(f'java_name found: {java_name}')
        content = content.replace('JAVA_NAME', java_name)

        # Write the slurm file to the destination folder
        slurm_name = f'r_{sample_id}.slurm'
        self.slurm_name[sample_id] = slurm_name
        dst = dst_folder / slurm_name
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(content)
        return 

    def run(self, sample_id):
        logger.info(f'Running sample for {sample_id} ')
        slurm_name = self.slurm_name[sample_id]


        # Check if the file exists
        if Path(self.check_file).exists() and self.rerun is False:
            pass
        else:
            if self.interactive_mode:
                cmd = f'chmod 777 {slurm_name}'
                os.system(cmd)
                os.system(f'./{slurm_name}')

            else:
                if self.partition == 'mit_preemptable':
                    cmd = f'sbatch --time {self.time_for_nodes} -N {self.n_nodes} --ntasks-per-node={self.n_cores} -p {self.partition} --nodelist=node[1600-1625,1917-1918] {slurm_name}'
                else:
                    cmd = f'sbatch --time {self.time_for_nodes} -N {self.n_nodes} --ntasks-per-node={self.n_cores} -p {self.partition} {slurm_name}'

                logger.debug(f'Running command: {cmd}')
                os.system(cmd)
        return

