@echo off
REM Add local Python 3.11 to the beginning of PATH
set PATH=%~dp0python 3.11;%~dp0python 3.11\Scripts;%PATH%

REM Verify the correct Python is now active
echo Verifying Python version...
python --version

REM Keep the command prompt open to the project directory
cd /d %~dp0
cmd /k
