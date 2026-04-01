#!/bin/bash
source ~/anaconda3/etc/profile.d/conda.sh 
conda activate
starccm18="/opt/Siemens/18.02.008-R8/STAR-CCM+18.02.008-R8/star/bin/starccm+"
sim_file="SIM_FILE_NAME"
n_prcs=N_CORES_FOR_COMPUTING

rm -f DONE
rm -f ABORT
rm -f JAVA_NAME.log


# IE Steady-state
java_name="run_uqss_Tall3D_IE"
$starccm18  $sim_file -printpids -batch -rsh ssh $java_name.java -on $n_prcs | tee -a $java_name.log

# generate rf
python grf.py

# ME

sim_file2=$(ls *.sim | grep '@')
java_name="run_uqss_Tall3D_GRF"
$starccm18  $sim_file2 -printpids -batch -rsh ssh $java_name.java -on $n_prcs | tee -a $java_name.log

touch DONE
