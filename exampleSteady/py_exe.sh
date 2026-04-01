#!/bin/bash
# module load anaconda3/2021.11
cat run_uqtr_Tall3D_BEPU_ME.log | grep Time | tail -n 1 > time
python grf.py


