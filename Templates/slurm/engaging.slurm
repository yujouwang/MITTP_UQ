#!/bin/bash
module load anaconda3/2022.10
env
cpus="$SLURM_CPUS_ON_NODE"
nodelistcompact="$SLURM_JOB_NODELIST"
nodelistfull=`scontrol show hostnames $nodelistcompact`
nodes=`echo $nodelistfull | sed 's/$/ /g' | sed 's/ /:32,/g'`
n_prcs=`echo $nodelistfull | sed 's/$/ /g' | sed 's/ /:'"$cpus,"'/g'`
host=`echo $nodelistfull | sed 's/$/ /g'`


echo --------
echo $n_prcs
echo -------

echo --------
echo $nodelistfull
echo -------


hostname="$HOSTNAME"


# 1 . Execute python
python grf.py


# 2. Execute Star

sim_file="SIM_FILE_NAME"
# Search for the java file in the same folder
java_file=$(find . -maxdepth 1 -type f -name "*.java" -printf "%T@ %p\n" | sort -nr | head -n 1 | cut -d' ' -f2-)

if [ -z "$java_file" ]; then
    echo "ERROR: No .java file found in current directory."
    touch ABORT
    exit 1
fi
echo "Using newest Java macro: $java_file"


# version="/home/yjouwang/18.02.008-R8/STAR-CCM+18.02.008-R8"
version="/home/rbrew/STAR-CCM+/19.04.009-R8/STAR-CCM+19.04.009-R8"

rm -f DONE
rm -f ABORT

${version}/star/bin/starccm+  $sim_file -printpids -batch -rsh ssh $java_file -on $n_prcs | tee -a log

touch DONE