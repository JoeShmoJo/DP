@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM -------------------------------------------------------------------
REM Always relaunch into a visible console unless already relaunched.
REM -------------------------------------------------------------------
if /I not "%~1"=="__IN_CONSOLE__" (
  start "ExternalPython Run" cmd /k "cd /d ""%~dp0"" && ""%~f0"" __IN_CONSOLE__ %*"
  exit /b
)
shift

REM ====== USER SETTINGS ======
set "ENV_NAME=hydro39"

REM Script is assumed to be in the SAME folder as this .bat (ExternalPython)
set "PY_SCRIPT=MainstemAugmentation.py"

REM Log folder (relative to this .bat)
set "LOG_DIR=logs"
REM ============================

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
  "& { & '%PYTHON_EXE%' '%SCRIPT%' %* 2>&1 | Tee-Object -FilePath '%LOG%' -Append; exit $LASTEXITCODE }"

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

REM Run from the BAT's directory (ExternalPython)
cd /d "%~dp0"

REM Ensure log directory exists
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

REM Timestamp for log file name: YYYYMMDD_HHMMSS
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"

set "LOG=%LOG_DIR%\run_%TS%.log"
set "LOG_LATEST=%LOG_DIR%\run_latest.log"

echo ===== %date% %time% =====> "%LOG%"
echo BAT_DIR=%~dp0>>"%LOG%"
echo ENV_NAME=%ENV_NAME%>>"%LOG%"
echo PY_SCRIPT=%PY_SCRIPT%>>"%LOG%"
echo.>>"%LOG%"

REM ---- locate conda root ----
set "CONDA_ROOT="

if exist "%LOCALAPPDATA%\miniconda3\envs" set "CONDA_ROOT=%LOCALAPPDATA%\miniconda3"
if exist "%LOCALAPPDATA%\anaconda3\envs"  set "CONDA_ROOT=%LOCALAPPDATA%\anaconda3"

if "%CONDA_ROOT%"=="" if exist "%USERPROFILE%\miniconda3\envs" set "CONDA_ROOT=%USERPROFILE%\miniconda3"
if "%CONDA_ROOT%"=="" if exist "%USERPROFILE%\anaconda3\envs"  set "CONDA_ROOT=%USERPROFILE%\anaconda3"
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

REM ---- verify script path ----
if not exist "%PY_SCRIPT%" (
    echo ERROR: Script not found: %CD%\%PY_SCRIPT%
    echo ERROR: Script not found: %CD%\%PY_SCRIPT%>>"%LOG%"
    dir /b>>"%LOG%" 2>&1
    exit /b 3
)

REM ---- run the one script ----
call :RunPy "%PY_SCRIPT%" "ExternalPython"

REM ---- copy to latest log ----
copy /y "%LOG%" "%LOG_LATEST%" >nul 2>&1

echo Done.
echo Done.>>"%LOG%"
exit /b 0