#!/bin/sh
#

#RESSIMDIR=/u/werner/hec/HEC-ResSim/3.1Alpha-II
RESSIMDIR=/u/werner/hec/HEC-ResSim/HEC-ResSim31_RC2_Build_9
PYSCRIPT=/u/werner/fews_nws/chps/cnrfc_cn/Models/hec/ressim/YubaFeatherFCO/script.py
MODELDIR=/u/werner/fews_nws/chps/cnrfc_cn/Models/hec/ressim/YubaFeatherFCO


echo on
pwd
umask

echo Argument 1: ResSim Directory : $RESSIMDIR > $MODELDIR/ResSim_Arguments.log
echo Argument 2: Python Script    : $PYSCRIPT >> $MODELDIR/ResSim_Arguments.log
echo Argument 3: ResSim Log file  : $MODELDIR >> $MODELDIR/ResSim_Arguments.log


# change current directory to root of ressim dir
cd $RESSIMDIR

echo Current dir: `pwd`


# unsetting the display (important when running in batch mode on FSS)
unset DISPLAY


$RESSIMDIR/HEC-ResSim-fews-adapter.sh $PYSCRIPT $MODELDIR 2>&1>$MODELDIR/ResSim_Linux.log
