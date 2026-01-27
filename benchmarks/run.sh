#!/bin/bash
source /etc/profile

cd /scratch/user/u.ks124812/ood_automl/benchmarks
 
/sw/local/bin/sbatch benchmark_ood_automl.job 
