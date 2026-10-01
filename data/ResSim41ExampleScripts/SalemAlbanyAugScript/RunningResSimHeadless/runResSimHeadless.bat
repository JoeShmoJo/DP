set runDirectory=%CD%
set resSimDirectory="C:\Data\WAT\HEC-WAT-v1.1.0.657-CRT_Modified\apps\HEC-ResSim"

REM use one of the lines below to send the command to run ResSim with a script
REM "%resSimDirectory%\HEC-ResSim" "%runDirectory%\%~n0.py"
"%resSimDirectory%\HEC-ResSim" "%runDirectory%\%~n0.py" "C:/Data/Tasks/District Models/NWS_VA/NWS_VA_HAH/test/debug_externalModules/NWS_Green" "NWS_Green" "NWS_Green.wksp" "2017.10.23-1200" "Test Run2"

pause