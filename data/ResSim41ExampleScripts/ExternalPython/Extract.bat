@echo off


setlocal EnableExtensions EnableDelayedExpansion

REM -------------------------------------------------------------------
REM Always relaunch into a visible console unless already relaunched.
REM This guarantees a terminal window appears when double-clicked.
REM -------------------------------------------------------------------
if /I not "%~1"=="__IN_CONSOLE__" (
  start "Extract" cmd /c "cd /d ""%~dp0"" && ""%~f0"" __IN_CONSOLE__ %*"
  exit /b
)
shift


REM ====== USER SETTINGS ======
set "SIM_NAME=SalemAlbanyAug"
set "ENV_NAME=hydro39"
set "PY_SCRIPT_1=RFC_Downloader_Module.py"
set "PY_SCRIPT_2=CWMS_Downloader_Module.py"
set "PY_SCRIPT_3=Dummy_0_and_WY_Abundant_Module.py"
set "PY_SCRIPT_4=OSI_Ensemble_Year.py"
set "LOG=bat_log.txt"
REM ============================

REM IMPORTANT: prevent fall-through into function labels
goto :MAIN


REM -------------------------------------------------------------------
REM RunPy: run python script, stream to console AND append to log
REM Uses PowerShell Tee-Object for true tee behavior.
REM -------------------------------------------------------------------
:RunPy
set "SCRIPT=%~1"
set "LABEL=%~2"

if "%SCRIPT%"=="" (
  echo ERROR: RunPy called with empty SCRIPT
  echo ERROR: RunPy called with empty SCRIPT>>"%LOG%"
  exit /b 99
)

if "%LABEL%"=="" set "LABEL=Script"

echo --- Running %LABEL%: %SCRIPT% ---
echo --- Running %LABEL%: %SCRIPT% --- >>"%LOG%"

echo CMD: "%PYTHON_EXE%" "%SCRIPT%" %*
echo CMD: "%PYTHON_EXE%" "%SCRIPT%" %*>>"%LOG%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "& { $env:SIM_NAME='%SIM_NAME%'; & '%PYTHON_EXE%' '%SCRIPT%' %* 2>&1 | Tee-Object -FilePath '%LOG%' -Append; exit $LASTEXITCODE }"
set "ERR=%ERRORLEVEL%"

echo %LABEL% ExitCode=%ERR%
echo %LABEL% ExitCode=%ERR%>>"%LOG%"

if not "%ERR%"=="0" (
    echo ERROR: %LABEL% failed; stopping.
    echo ERROR: %LABEL% failed; stopping.>>"%LOG%"
    exit /b %ERR%
)

exit /b 0


REM -------------------------------------------------------------------
REM MAIN
REM -------------------------------------------------------------------
:MAIN

echo ===== %date% %time% =====
echo ===== %date% %time% =====>>"%LOG%"

REM ---- locate conda root ----
set "CONDA_ROOT="

if exist "%LOCALAPPDATA%\miniconda3\envs" set "CONDA_ROOT=%LOCALAPPDATA%\miniconda3"
if exist "%LOCALAPPDATA%\anaconda3\envs"  set "CONDA_ROOT=%LOCALAPPDATA%\anaconda3"

if "%CONDA_ROOT%"=="" if exist "%USERPROFILE%\miniconda3\envs"  set "CONDA_ROOT=%USERPROFILE%\miniconda3"
if "%CONDA_ROOT%"=="" if exist "%USERPROFILE%\anaconda3\envs"   set "CONDA_ROOT=%USERPROFILE%\anaconda3"
if "%CONDA_ROOT%"=="" if exist "C:\ProgramData\miniconda3\envs" set "CONDA_ROOT=C:\ProgramData\miniconda3"
if "%CONDA_ROOT%"=="" if exist "C:\ProgramData\anaconda3\envs"  set "CONDA_ROOT=C:\ProgramData\anaconda3"
if "%CONDA_ROOT%"=="" if exist "C:\Miniconda3\envs"             set "CONDA_ROOT=C:\Miniconda3"
if "%CONDA_ROOT%"=="" if exist "C:\Anaconda3\envs"              set "CONDA_ROOT=C:\Anaconda3"
if "%CONDA_ROOT%"=="" if exist "C:\Programs\Anaconda3\envs"     set "CONDA_ROOT=C:\Programs\Anaconda3"
if "%CONDA_ROOT%"=="" if exist "C:\Programs\Miniconda3\envs"    set "CONDA_ROOT=C:\Programs\Miniconda3"
if "%CONDA_ROOT%"=="" if exist "C:\Programs\anaconda3\envs"     set "CONDA_ROOT=C:\Programs\Anaconda3"
if "%CONDA_ROOT%"=="" if exist "C:\Programs\miniconda3\envs"    set "CONDA_ROOT=C:\Programs\Miniconda3"

if "%CONDA_ROOT%"=="" (
    echo ERROR: Could not locate Conda installation
    echo ERROR: Could not locate Conda installation>>"%LOG%"
    echo LOCALAPPDATA=%LOCALAPPDATA%>>"%LOG%"
    echo USERPROFILE=%USERPROFILE%>>"%LOG%"
    exit /b 1
)

echo Found CONDA_ROOT=%CONDA_ROOT%
echo Found CONDA_ROOT=%CONDA_ROOT%>>"%LOG%"

REM ---- locate env python ----
set "PYTHON_EXE=%CONDA_ROOT%\envs\%ENV_NAME%\python.exe"

if not exist "%PYTHON_EXE%" (
    echo ERROR: Env python not found: %PYTHON_EXE%
    echo ERROR: Env python not found: %PYTHON_EXE%>>"%LOG%"
    echo Available envs in %CONDA_ROOT%\envs :>>"%LOG%"
    dir /b "%CONDA_ROOT%\envs" >>"%LOG%" 2>&1
    exit /b 2
)

echo Using PYTHON_EXE=%PYTHON_EXE%
echo Using PYTHON_EXE=%PYTHON_EXE%>>"%LOG%"

REM ---- run scripts ----
call :RunPy "%PY_SCRIPT_1%" "Script1"
call :RunPy "%PY_SCRIPT_2%" "Script2"
call :RunPy "%PY_SCRIPT_3%" "Script3"
call :RunPy "%PY_SCRIPT_4%" "Script4"

echo Done.
echo Done.>>"%LOG%"
exit /b 0