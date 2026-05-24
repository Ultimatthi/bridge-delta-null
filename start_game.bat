@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
set "PY_VERSION=3.12.10"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-embed-amd64.zip"
set "PY_DIR=%~dp0python_env"
set "PY_EXE=%PY_DIR%\python.exe"
set "SCRIPT_NAME=cardgame.py"

title Starting game...

:: Skip setup if Python is already installed
if exist "%PY_EXE%" goto :RUN_GAME

echo ===================================================
echo First-time setup (one-time only, approx. 15 MB)...
echo ===================================================

:: [1/4] Download embedded Python from python.org
echo [1/4] Downloading Python...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile 'python_embed.zip' -ErrorAction Stop"
if !errorlevel! neq 0 ( echo ERROR: Download failed! Please check your internet connection. & pause & exit /b )

:: [2/4] Extract the zip into the local python_env folder
echo [2/4] Extracting Python...
powershell -Command "Expand-Archive -Path 'python_embed.zip' -DestinationPath '%PY_DIR%' -Force"
del python_embed.zip

:: [3/4] Enable pip support and inject game directory into Python path
::       Embedded Python ignores PYTHONPATH, so we patch the .pth file directly.
::       "import site" allows third-party packages to be found.
::       ".." adds the parent folder (game directory) so local modules like logic/ are found.
echo [3/4] Enabling pip support and local paths...
powershell -Command "(Get-Content '%PY_DIR%\python312._pth') -replace '#import site','import site' | Set-Content '%PY_DIR%\python312._pth'"
powershell -Command "Add-Content '%PY_DIR%\python312._pth' '..'"

:: [4/4] Install pip, then install all required packages
echo [4/4] Installing pip and packages...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PY_DIR%\get-pip.py' -ErrorAction Stop"
if !errorlevel! neq 0 ( echo ERROR: pip download failed! Please check your internet connection. & pause & exit /b )
"%PY_EXE%" "%PY_DIR%\get-pip.py" --quiet --no-warn-script-location
del "%PY_DIR%\get-pip.py"

echo Installing arcade, numpy, pyperclip, endplay...
"%PY_EXE%" -m pip install arcade numpy pyperclip endplay --quiet --no-warn-script-location
if !errorlevel! neq 0 ( echo ERROR: Package installation failed. & pause & exit /b )

:: --- START GAME ---
:RUN_GAME
echo Starting %SCRIPT_NAME%...
cd /d "%~dp0"
"%PY_EXE%" "%SCRIPT_NAME%"
if !errorlevel! neq 0 ( echo The game exited with an error. & pause )

endlocal