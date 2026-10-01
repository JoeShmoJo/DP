#!/bin/sh
#This script runs changes the directory to the HEC-ResSim directory
#to the directory specified in arg $1 and executes the DSS_FCO_ResSim.sh 
#with a script arg. $2
echo on
umask ugo+rwx

cd $1

./DSS_FCO_HEC-ResSim.sh $2
exit 0




