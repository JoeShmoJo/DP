#!/bin/bash
#
PYSCRIPT=$1
MODELDIR=$2

# If there are arguments passed (a script), start Xvfb and set DISPLAY
if [ $# -ne 0 ]
then
	unset DISPLAY
	XvfbRunning=`ps -ef | grep Xvfb | grep -v grep | wc -l | sed -e "s/ //g"`
	# start Xfvb if this is not running
	if [ $XvfbRunning -eq 0 ]
	then
		printf "\nStarting Xvfb...\n\n"
		Xvfb :99 -ac -screen 0 1280x1024x8 &
		sleep 5
	fi
	XvfbRunning=`ps -ef | grep Xvfb | grep -v grep | wc -l | sed -e "s/ //g"`
	if [ $XvfbRunning -gt 0 ]
	then
		DISPLAY=":99.0"
		export DISPLAY
	else
		printf "Virtual display server is not running.\n"
		printf "Set DISPLAY variable or start Xvfb.\n"
		exit
	fi
fi
if [ -z "$DISPLAY" ]; then
        printf "\nThe DISPLAY variable is not set, and no script was passed to HEC-ResSim. There is nothing to do.\n\n"
        exit
fi

#
# PROG_ROOT=/usr/local/hec/HEC-ResSim/3.1
PROG_ROOT=.
JAVA_EXE=$PROG_ROOT/java/bin/java
JARDIR=$PROG_ROOT/jar
JARDIRSYS=$PROG_ROOT/jar/sys

APPJARS="$JARDIR/hec.jar:$APPJARS"
APPJARS="$JARDIR/hecData.jar:$APPJARS"
APPJARS="$JARDIR/heclib.jar:$APPJARS"
APPJARS="$JARDIR/images.jar:$APPJARS"
APPJARS="$JARDIR/mrSidReader.jar:$APPJARS"
APPJARS="$JARDIR/msgSystem.jar:$APPJARS"
APPJARS="$JARDIR/resprm.jar:$APPJARS"
APPJARS="$JARDIR/rma.jar:$APPJARS"
APPJARS="$JARDIR/rss.jar:$APPJARS"

SYSJARS="$JARDIRSYS/codebase.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jai_codec.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jai_core.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jai_imageio.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jdom.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jh.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jxl.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jython.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jythonlib.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jythonUtils.jar:$SYSJARS"



JARS="$APPJARS:$SYSJARS"

APPDATA=`echo ~/.HEC/HEC-ResSim/3.1`

echo $PYSCRIPT
echo $MODELDIR

$JAVA_EXE -ms4M -mx400M -DAsciiSerializer.formatFile=true -Dlogfile.directory=$MODELDIR -DLOGFILE=$MODELDIR/ResSim.log -DCACHE_DIR=$APPDATA/cache -Dpython.home=$APPDATA/pythonHome -Dlogin.properties.path=$PROG_ROOT/config/login.properties -Djava.library.path=$PROG_ROOT/lib -Dproperties.path=$PROG_ROOT/config -DCWMS_HOME=$APPDATA -DCWMS_EXE=$PROG_ROOT -Djava.security.policy=$PROG_ROOT/config/java.policy -DstatePlane.directory=$PROG_ROOT/config -cp "$JARS" hec.rss.client.RSS $PYSCRIPT

