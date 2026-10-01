rem Installs Save_Scripts and Load_Scripts
rem Run this to put the scripts into ResSim
rem so that you can launch them from the
rem Tools->Scripts window
rem
rem Note, this will need to be updated with
rem each minor version of ResSim used.

rem copy .\Save_Scripts.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\Save_Scripts.py
rem copy .\Load_Scripts.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\Load_Scripts.py

xcopy /s/e /Y /F /I Save_Scripts.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\
xcopy /s/e /Y /F /I Load_Scripts.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\
xcopy /s/e /Y /F /I Rules_to_CSV.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\
xcopy /s/e /Y /F /I DeleteUnusedRules.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\
xcopy /s/e /Y /F /I DeleteUnusedOpSets.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\
xcopy /s/e /Y /F /I ElevStor_to_CSV.py %APPDATA%\HEC\HEC-ResSim\3.5\users\CWMS\All\scripts\Modules\Reservoir_Network\
pause