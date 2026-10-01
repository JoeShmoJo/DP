@echo off
setlocal EnableExtensions

REM === Set this to the ResSim you KNOW can run scripts (CWMS install is usually safest) ===
set "RESSIM_DIR=C:\Mobile_Programs\cwms-cavi-install-package-3.5.0\CWMS-3.5.0\HEC-ResSim\3.5.1"

REM === Your watershed inputs ===
set "WSDIR=C:\Projects\FIRO\NWP_Willamette_Master_2025-12-11-FOS_NoOvertop"
set "WSNAME=NWP_Willamette_Master_2025-12-11-FOS_NoOvertop"
set "WKSPFILE=NWP_Willamette_Master_2025-12-11-FOS_NoOvertop.wksp"
set "SIMNAME=Headless_Compute"
set "RUNNAME=Temp1Day"

REM Run the Jython script (same folder as this BAT)
"%RESSIM_DIR%\HEC-ResSim.exe" "%~dp0RunResSim_Headless.py" ^
  "%WSDIR%" ^
  "%WSNAME%" ^
  "%WKSPFILE%" ^
  "%SIMNAME%" ^
  "%RUNNAME%"

echo ExitCode=%ERRORLEVEL%
pause