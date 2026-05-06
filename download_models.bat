@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "VENV_DIR=%ROOT%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "MODEL_ROOT=%ROOT%models"
set "SMALL_MODEL_DIR=%MODEL_ROOT%\small"
set "MEDIUM_MODEL_DIR=%MODEL_ROOT%\medium"
set "DOWNLOAD_FAILURES=0"

echo.
echo Offline Whisper Subtitle Generator - Model Download
echo Project root: "%ROOT%"
echo.

if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment Python was not found.
    echo Dependencies not installed. Please run install_cpu.bat or install_gpu.bat first.
    exit /b 1
)

echo Creating model and cache folders...
for %%D in (
    "models"
    "models\small"
    "models\medium"
    "cache"
    "cache\huggingface"
    "cache\huggingface\hub"
    "cache\transformers"
    "cache\torch"
    "cache\pip"
    "temp"
) do (
    if not exist "%ROOT%%%~D" mkdir "%ROOT%%%~D"
)
if errorlevel 1 (
    echo ERROR: Failed to create required model/cache folders.
    exit /b 1
)

set "HF_HOME=%ROOT%cache\huggingface"
set "HUGGINGFACE_HUB_CACHE=%ROOT%cache\huggingface\hub"
set "TRANSFORMERS_CACHE=%ROOT%cache\transformers"
set "TORCH_HOME=%ROOT%cache\torch"
set "XDG_CACHE_HOME=%ROOT%cache"
set "TEMP=%ROOT%temp"
set "TMP=%ROOT%temp"
set "PIP_CACHE_DIR=%ROOT%cache\pip"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

echo Verifying huggingface_hub is available...
"%VENV_PYTHON%" -c "import huggingface_hub; print('huggingface_hub import OK')"
if errorlevel 1 (
    echo ERROR: huggingface_hub is not installed in the virtual environment.
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat.
    exit /b 1
)

call :download_model "Systran/faster-whisper-small" "%SMALL_MODEL_DIR%" "small"
if errorlevel 1 set /a DOWNLOAD_FAILURES+=1

call :download_model "Systran/faster-whisper-medium" "%MEDIUM_MODEL_DIR%" "medium"
if errorlevel 1 set /a DOWNLOAD_FAILURES+=1

echo.
if "%DOWNLOAD_FAILURES%"=="0" (
    echo Model download step completed successfully.
    echo Models ready:
    echo - "%SMALL_MODEL_DIR%"
    echo - "%MEDIUM_MODEL_DIR%"
    exit /b 0
)

echo Model download completed with %DOWNLOAD_FAILURES% failure(s).
echo Model download failed. Check internet connection or Hugging Face access. You may need to manually download the model.
exit /b 1

:download_model
set "REPO_ID=%~1"
set "TARGET_DIR=%~2"
set "MODEL_NAME=%~3"

echo.
echo Checking %MODEL_NAME% model: %REPO_ID%
call :verify_model_files "%TARGET_DIR%"
if not errorlevel 1 (
    echo %MODEL_NAME% model is already complete. Skipping download.
    exit /b 0
)

echo %MODEL_NAME% model is missing or incomplete. Downloading to:
echo "%TARGET_DIR%"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

"%VENV_PYTHON%" -c "import sys; exec('''from huggingface_hub import snapshot_download\nrepo_id = sys.argv[1]\nlocal_dir = sys.argv[2]\ntry:\n    snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False)\nexcept Exception as exc:\n    text = str(exc)\n    response = getattr(exc, 'response', None)\n    status = getattr(response, 'status_code', None)\n    print('Model download failed. Check internet connection or Hugging Face access. You may need to manually download the model.')\n    if status in (401, 403) or '401' in text or '403' in text:\n        print('Authorization error (401/403) while downloading ' + repo_id + '.')\n    else:\n        print('Network or download error while downloading ' + repo_id + ': ' + text)\n    raise SystemExit(1)\n''')" "%REPO_ID%" "%TARGET_DIR%"
if errorlevel 1 (
    echo ERROR: Download failed for %REPO_ID%.
    echo Continuing to the next model if any.
    exit /b 1
)

call :verify_model_files "%TARGET_DIR%"
if errorlevel 1 (
    echo ERROR: Download for %REPO_ID% finished, but required model files are incomplete.
    echo Required files: model.bin, config.json, tokenizer.json, vocabulary.txt
    echo Model download failed. Check internet connection or Hugging Face access. You may need to manually download the model.
    exit /b 1
)

echo %MODEL_NAME% model verified successfully.
exit /b 0

:verify_model_files
set "CHECK_DIR=%~1"
if not exist "%CHECK_DIR%\model.bin" exit /b 1
if not exist "%CHECK_DIR%\config.json" exit /b 1
if not exist "%CHECK_DIR%\tokenizer.json" exit /b 1
if not exist "%CHECK_DIR%\vocabulary.txt" exit /b 1
exit /b 0
