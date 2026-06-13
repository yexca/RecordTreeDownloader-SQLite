@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "PYTHON_VERSION=3.12.10"
set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "ENV_DIR=%ROOT_DIR%\env"

set "LOCAL_PYTHON_DIR=%ENV_DIR%\python"
set "LOCAL_PYTHON=%LOCAL_PYTHON_DIR%\python.exe"
set "VENV_DIR=%ROOT_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "RECORDTREE_EXE=%VENV_DIR%\Scripts\recordtree.exe"
set "PYTHON_INSTALLER=%ENV_DIR%\python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"

echo [RecordTreeDownloader] Preparing local environment...
if not exist "%ENV_DIR%" mkdir "%ENV_DIR%"

if exist "%LOCAL_PYTHON%" (
    set "BASE_PYTHON=%LOCAL_PYTHON%"
    goto :create_venv
)

for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable if sys.version_info >= (3, 11) else '')" 2^>nul') do set "BASE_PYTHON=%%P"
if not defined BASE_PYTHON (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable if sys.version_info >= (3, 11) else '')" 2^>nul') do set "BASE_PYTHON=%%P"
)
if defined BASE_PYTHON echo [RecordTreeDownloader] Found Python 3.11+: %BASE_PYTHON%
if defined BASE_PYTHON goto :create_venv

echo [RecordTreeDownloader] Python 3.11+ was not found. Installing Python %PYTHON_VERSION% into env\python...
call :download_python || exit /b 1

start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%LOCAL_PYTHON_DIR%" Include_pip=1 Include_launcher=0 PrependPath=0 Shortcuts=0 Include_test=0 Include_tcltk=0 SimpleInstall=1
if errorlevel 1 (
    echo [RecordTreeDownloader] Python installer failed.
    exit /b 1
)

if not exist "%LOCAL_PYTHON%" (
    echo [RecordTreeDownloader] Python installer completed, but python.exe was not found at:
    echo %LOCAL_PYTHON%
    exit /b 1
)
if exist "%PYTHON_INSTALLER%" del /q "%PYTHON_INSTALLER%"

set "BASE_PYTHON=%LOCAL_PYTHON%"

:create_venv
if not exist "%VENV_PYTHON%" (
    echo [RecordTreeDownloader] Creating virtual environment in .venv...
    "%BASE_PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [RecordTreeDownloader] Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo [RecordTreeDownloader] Reusing existing virtual environment.
)

echo [RecordTreeDownloader] Installing project dependencies locally...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%VENV_PYTHON%" -m pip install -e "%ROOT_DIR%[dev]"
if errorlevel 1 exit /b 1

echo [RecordTreeDownloader] Initializing config and database...
"%RECORDTREE_EXE%" init
if errorlevel 1 exit /b 1

echo.
echo [RecordTreeDownloader] Environment is ready.
echo Python: %VENV_PYTHON%
echo Run: "%RECORDTREE_EXE%" doctor
echo Run: "%RECORDTREE_EXE%" import "%ROOT_DIR%\files\Record Tree 260605.xlsx"
exit /b 0

:download_python
if exist "%PYTHON_INSTALLER%" (
    echo [RecordTreeDownloader] Reusing downloaded installer: %PYTHON_INSTALLER%
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 (
    echo [RecordTreeDownloader] Failed to download Python installer:
    echo %PYTHON_URL%
    exit /b 1
)
exit /b 0
