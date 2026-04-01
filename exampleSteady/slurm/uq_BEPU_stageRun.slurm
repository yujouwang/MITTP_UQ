#!/bin/bash
# module load anaconda3/2022.10
source /orcd/home/002/yjouwang/anaconda3/etc/profile.d/conda.sh
conda activate
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

sim_file="SIM_FILE_NAME"


version="/home/yjouwang/18.02.008-R8/STAR-CCM+18.02.008-R8"

rm -f DONE
rm -f ABORT
rm -f JAVA_NAME.log


# Transient - Co-sim
# ${version}/star/bin/starlaunch --resources $n_prcs --command "${version}/star/bin/starccm+ -batch JAVA_NAME.java SIM_FILE_NAME" --slots N_CORES_FOR_COMPUTING >> JAVA_NAME.log

# IE Steady-state
java_name="run_uqss_Tall3D_IE"
${version}/star/bin/starccm+  $sim_file -printpids -batch -rsh ssh $java_name.java -on $n_prcs | tee -a $java_name.log

# generate rf
python grf.py

# ME
# search for the new sim file name containing '@'
sim_file2=$(ls *.sim | grep '@')
java_name="run_uqss_Tall3D_GRF"
${version}/star/bin/starccm+  $sim_file2 -printpids -batch -rsh ssh $java_name.java -on $n_prcs | tee -a $java_name.log

touch DONE
