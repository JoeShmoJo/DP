#!/bin/sh
#
RESSIMDIR=$1
PYSCRIPT=$2
MODELDIR=$3

echo on
pwd
umask

echo Argument 1: ResSim Directory : $RESSIMDIR > $MODELDIR/ResSim_Arguments.log
echo Argument 2: Python Script    : $PYSCRIPT >> $MODELDIR/ResSim_Arguments.log
echo Argument 3: ResSim Log file  : $MODELDIR >> $MODELDIR/ResSim_Arguments.log


# change current directory to root of ressim dir
cd $RESSIMDIR


# unsetting the display (important when running in batch mode on FSS)
unset DISPLAY

$RESSIMDIR/HEC-ResSim-fews-adapter.sh $PYSCRIPT $MODELDIR 2>&1>$MODELDIR/ResSim_Linux.log
