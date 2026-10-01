#!/bin/bash
#

# If there are arguments passed (a script), start Xvfb and set DISPLAY
if [ $# -ne 0 ]
then
	unset DISPLAY
	XvfbRunning=`ps -ef | grep Xvfb | grep -v grep | wc -l | sed -e "s/ //g"`
	# start Xfvb if this is not running
	if [ $XvfbRunning -eq 0 ]
	then
		printf "\nStarting Xvfb...\n\n"
		sleep 2
		Xvfb :99 -ac -screen 0 1280x1024x8 &
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

#PROG_ROOT=/usr/local/hec/HEC-ResSim/HEC-ResSim_3.2.1.22_Dev_Build
PROG_ROOT=.

JAVA_EXE=$PROG_ROOT/java/bin/java

# JAVA_EXE=/usr/java/jdk1.7.0_51_x86/jre/bin/java
# JAVA_EXE=/usr/lib/jvm/java-1.7.0-openjdk-1.7.0.45.x86_64/jre/bin/java

JARDIR=$PROG_ROOT/jar
JARDIRSYS=$PROG_ROOT/jar/sys
JARDIREXT=$PROG_ROOT/jar/ext

APPJARS="$JARDIR/callbackServices.jar:$APPJARS"
APPJARS="$JARDIR/hec.jar:$APPJARS"
APPJARS="$JARDIR/hecData.jar:$APPJARS"
APPJARS="$JARDIR/heclib.jar:$APPJARS"
APPJARS="$JARDIR/images.jar:$APPJARS"
APPJARS="$JARDIR/lookup.jar:$APPJARS"
APPJARS="$JARDIR/mrSidReader.jar:$APPJARS"
APPJARS="$JARDIR/msgSystem.jar:$APPJARS"
APPJARS="$JARDIR/rma.jar:$APPJARS"
APPJARS="$JARDIR/rss.jar:$APPJARS"

SYSJARS="$JARDIRSYS/codebase.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/colt.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jai_codec.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jai_core.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jai_imageio.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jcommon.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jdom.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jh.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/junit.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jfreechart.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jxl.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jython.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jythonlib.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/jythonUtils.jar:$SYSJARS"
SYSJARS="$JARDIRSYS/rsyntaxtextarea.jar:$SYSJARS"

EXTJARS="$JARDIREXT/CollectionUtilities.jar:$EXTJARS"
EXTJARS="$JARDIREXT/dssvueHelp.jar:$EXTJARS"
EXTJARS="$JARDIREXT/ensemblePlugin.jar:$EXTJARS"
EXTJARS="$JARDIREXT/ExcelDssVuePlugin.jar:$EXTJARS"
EXTJARS="$JARDIREXT/montecarloPlugin.jar:$EXTJARS"
EXTJARS="$JARDIREXT/w2Plugin.jar:$EXTJARS"

JARS="$APPJARS:$SYSJARS:$EXTJARS"
#APPDATA=`echo ~/.HEC/HEC-ResSim/3.2`

APPDATA=`echo /usr/local/hec/HEC-ResSim/HECDATA`


$JAVA_EXE -ms32M -mx2048M -DAsciiSerializer.formatFile=true -Dlogfile.directory=$APPDATA/logs -DLOGFILE=$APPDATA/logs/HEC-ResSim.log -DCACHE_DIR=$APPDATA/cache -Dpython.home=$APPDATA/pythonHome -Dlogin.properties.path=$PROG_ROOT/config/login.properties -Djava.library.path=$PROG_ROOT/lib -Dproperties.path=$PROG_ROOT/config -DCWMS_HOME=$APPDATA -DCWMS_EXE=$PROG_ROOT -Djava.security.policy=$PROG_ROOT/config/java.policy -DstatePlane.directory=$PROG_ROOT/config -cp "$JARS" hec.rss.client.RSS $1



#$JAVA_EXE -ms768M -mx2048M -DAsciiSerializer.formatFile=true -Dlogfile.directory=$APPDATA/logs -DLOGFILE=$APPDATA/logs/HEC-ResSim.log -DCACHE_DIR=$APPDATA/cache -Dpython.home=$APPDATA/pythonHome -Dlogin.properties.path=$PROG_ROOT/config/login.properties -Djava.library.path=$PROG_ROOT/lib -Dproperties.path=$PROG_ROOT/config -DCWMS_HOME=$APPDATA -DCWMS_EXE=$PROG_ROOT -Djava.security.policy=$PROG_ROOT/config/java.policy -DstatePlane.directory=$PROG_ROOT/config -cp "$JARS" hec.rss.client.RSS $1




#$JAVA_EXE -ms4M -mx400M -DAsciiSerializer.formatFile=true -Dlogfile.directory=$APPDATA/logs -DLOGFILE=$APPDATA/logs/HEC-ResSim.log -DCACHE_DIR=$APPDATA/cache -Dpython.home=$APPDATA/pythonHome -Dlogin.properties.path=$PROG_ROOT/config/login.properties -Djava.library.path=$PROG_ROOT/lib -Dproperties.path=$PROG_ROOT/config -DCWMS_HOME=$APPDATA -DCWMS_EXE=$PROG_ROOT -Djava.security.policy=$PROG_ROOT/config/java.policy -DstatePlane.directory=$PROG_ROOT/config -cp "$JARS" hec.rss.client.RSS $1

# Last versions command line.
#$JAVA_EXE -ms4M -mx400M -DAsciiSerializer.formatFile=true -Dlogfile.directory=$APPDATA/logs -DLOGFILE=$APPDATA/logs/HEC-ResSim.log -DCACHE_DIR=$APPDATA/cache -Dpython.home=$APPDATA/pythonHome -Dlogin.properties.path=$PROG_ROOT/config/login.properties -Djava.library.path=$PROG_ROOT/lib -Dproperties.path=$PROG_ROOT/config -DCWMS_HOME=$APPDATA -DCWMS_EXE=$PROG_ROOT -Djava.security.policy=$PROG_ROOT/config/java.policy -DstatePlane.directory=$PROG_ROOT/config -cp "$JARS" hec.rss.client.RSS $1

#$JAVA_EXE -ms4M -mx400M -DAsciiSerializer.formatFile=true -Dlogfile.directory=$APPDATA/logs -DLOGFILE=$APPDATA/logs/HEC-ResSim.log -DCACHE_DIR=$APPDATA/cache -Dpython.home=$APPDATA/pythonHome -Dlogin.properties.path=$PROG_ROOT/config/login.properties -Djava.library.path=$PROG_ROOT/lib -Dproperties.path=$PROG_ROOT/config -DCWMS_HOME=$APPDATA -DCWMS_EXE=$PROG_ROOT -Djava.security.policy=$PROG_ROOT/config/java.policy -DstatePlane.directory=$PROG_ROOT/config -cp "$JARS" hec.rss.client.RSS $1
exit 0
