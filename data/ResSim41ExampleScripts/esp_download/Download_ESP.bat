@echo on
SETLOCAL ENABLEEXTENSIONS
setlocal EnableDelayedExpansion
title Download ESP
rem Finding the most current version of R installed and running script
rem executable path should be something like this: "C:\Program Files\R\R-3.3.2\bin\x64\R.exe"

rem The assumed script name
set basedir=%cd%
set scriptname=%cd%/"ESP Download.R"
set dssfile="columbia10_6hr.dss"

echo Executing the following script: %scriptname%

rem set executablepath=D:\crt_crso\FRA_Plotter_v4.6.1\resources\R-3.4.2\bin\x64\Rscript.exe
set executablepath="D:\ESP Set up\R-3.4.2\bin\x64\Rscript.exe"
echo Executing R from the following executable: %executablepath%


rem arguments to pass to the script
cd ../../shared
set args=%cd%/%dssfile%

@echo on
set eval=%executablepath% --vanilla %scriptname% %args%

cd scripts/esp_download
echo evaluating the following expression: %eval%

%eval%

@echo off
echo Finished Execution of script.
