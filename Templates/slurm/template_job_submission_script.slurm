#!/bin/bash

# 1. Execute python
source ~/anaconda3/etc/profile.d/conda.sh 
conda activate
python grf.py

if [ ! -f "cov_matrix.csv" ]; then
    echo "ERROR: cov_matrix.csv was not generated after running grf.py."
    touch ABORT
    exit 1
fi


# 2. Execute STARCCM+

# Specify the STARCCM path
starccm19="/opt/Siemens/19.04.009-R8/STAR-CCM+19.04.009-R8/star/bin/starccm+"
rm -f DONE
rm -f ABORT
sim_file="SIM_FILE_NAME" # same as baseline sim specified by uq_config.yaml. will be replaced by job_manager
n_prcs=N_CORES # specified in uq_config.yaml. will be replaced by job_manager

# Search for the java file in the same folder
java_file=$(find . -maxdepth 1 -type f -name "*.java" -printf "%T@ %p\n" | sort -nr | head -n 1 | cut -d' ' -f2-)

if [ -z "$java_file" ]; then
    echo "ERROR: No .java file found in current directory."
    touch ABORT
    exit 1
fi

echo "Using newest Java macro: $java_file"
$starccm19  $sim_file -batch $java_file -np $n_prcs | tee -a log


touch DONE