@echo off
REM Where you run from becomes the "run directory"
set runDirectory=%CD%

REM Point this to your ResSim program folder (no trailing backslash in the variable value)
set resSimDirectory="C:\Mobile_Programs\cwms-cavi-install-package-3.5.0\CWMS-3.5.0\HEC-ResSim\3.5.1"

REM Launch ResSim headless with the Python/Jython script of the same base name,
REM and pass: <watershedDir> <watershedName> <watershedWkspName> <simulationName> <alternativeName>
"%resSimDirectory%\HEC-ResSim.exe" "%runDirectory%\%~n0.py" ^
 "C:\CWMS\watershed\Willamette2026" ^
 "Willamette2026" ^
 "Willamette2026.wksp" ^
 "13Feb2026" ^
 "Temp1Day"

pause
