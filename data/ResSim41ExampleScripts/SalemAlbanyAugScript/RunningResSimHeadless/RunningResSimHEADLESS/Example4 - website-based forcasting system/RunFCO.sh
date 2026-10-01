#!/bin/sh
#Description: This script runs the FCO_DSS Management script.
#	Requirements: 
#		Arg[0] = path to file
#		Arg[1] = EXEC OR INCOMING
#Note: 	If no arguements are specified, this ManageExec.py will process all files
#	in the Incoming queue folder. 

# when running as root - make sure HOME points to folder with data
# export makes it available to child processes
HOME=/home/hec
export HOME
unset DISPLAY

#Important: Specify the jython libraries here. Jython2.2 is require to run DSS_FCO
# JYTHONLIB="/usr/share/jython2.2/Lib"
# JYTHON22="/usr/share/jython2.2/jython.jar"

JYTHONLIB="/usr/share/jython2.7b1_32Bit_JVM/Lib"
JYTHON22="/usr/share/jython2.7b1_32Bit_JVM/jython.jar"

# RESSIM="/usr/local/hec/HEC-ResSim/HEC-ResSim_3.2.1.22_Dev_Build"
RESSIM="/usr/local/hec/HEC-ResSim/HEC-ResSim_3.2.1.43_Dev_Build"

#Heclib jars are in the bin folder.
EXECDIR="/usr/local/hec/HEC-ResSim/DSS_FCO/bin/"
HECLIB="$EXECDIR/lib"


JAVA_EXE=$RESSIM/java/bin/java

JARDIR=$EXECDIR/jar
JARDIRSYS=$JARDIR/sys
#Ensemble jars are in the etc directory
JARETC=$JARDIR/ext

APPJARS="$JARDIR/heclib.jar"
APPJARS="$JARDIR/hecData.jar:$APPJARS"
APPJARS="$JARDIR/gridUtil.jar:$APPJARS"
APPJARS="$JARDIR/hec.jar:$APPJARS"
APPJARS="$JARDIR/rma.jar:$APPJARS"
APPJARS="$JARDIR/images.jar:$APPJARS"
APPJARS="$JARDIR/commons-math3-3.2.jar:$APPJARS"
APPJARS="$JARDIR/joda-time-2.3.jar:$APPJARS"
APPJARS="$JARDIR/YCWAFCO.jar:$APPJARS"
APPJARS="$JARETC/CollectionUtilities.jar:$APPJARS"
APPJARS="$JARETC/ensemblePlugin.jar:$APPJARS"


JARDIR=$EXECDIR/jar
JARDIRSYS=$JARDIR/sys

JARS="$JYTHON22:$JYTHONLIB:$APPJARS" 
#DPYTHON_PATH="$JYTHON22:$JYTHONLIB:$RESSIM/java/lib/rt.jar:$HECLIB"
DPYTHON_PATH="$JYTHON22:$JYTHONLIB:usr/java/jdk1.7.0_51_x86/lib/rt.jar:$HECLIB"

cd $EXECDIR
$JAVA_EXE -classpath $JARS -Dpython.path=$DPYTHON_PATH -Djava.library.path=$HECLIB org.python.util.jython ManageExec.py $1 $2 >$3
exit 0




