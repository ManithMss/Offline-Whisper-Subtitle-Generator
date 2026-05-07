@echo off
setlocal EnableExtensions

REM Add local Python 3.11 to PATH priority
set "ROOT=%~dp0"
set "PATH=%ROOT%python 3.11;%ROOT%python 3.11\Scripts;%PATH%"
set "VENV_DIR=%ROOT%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS=%ROOT%requirements.txt"
set "TORCH_INDEX_URL="
set "CUDA_VERSION="
set "GPU_NAME="

echo.
echo Offline Whisper Subtitle Generator - GPU Setup
echo Project root: "%ROOT%"
echo Python 3.11 is recommended for this project.
echo.

if not exist "%REQUIREMENTS%" (
    echo ERROR: requirements.txt was not found.
    echo Expected: "%REQUIREMENTS%"
    exit /b 1
)

echo Creating required project folders...
for %%D in (
    "ffmpeg"
    "ffmpeg\bin"
    "models"
    "models\small"
    "models\medium"
    "cache"
    "cache\huggingface"
    "cache\huggingface\hub"
    "cache\transformers"
    "cache\torch"
    "cache\pip"
    "logs"
    "temp"
    "output_subtitles"
    "processed"
    "videos"
    "videos\japanese"
    "videos\russian"
    "videos\english"
    "videos\hindi"
    "videos\auto_detect"
) do (
    if not exist "%ROOT%%%~D" mkdir "%ROOT%%%~D"
)
if errorlevel 1 (
    echo ERROR: Failed to create required folders.
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
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

echo Checking Python version...
for /f "tokens=*" %%V in ('python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')"') do set PYVER=%%V

if not defined PYVER (
    echo ERROR: Python was not found on PATH.
    echo Install Python 3.11, then rerun install_gpu.bat.
    exit /b 1
)

echo Detected Python %PYVER%.
if "%PYVER%"=="3.10" goto python_ok
if "%PYVER%"=="3.11" goto python_ok

echo ERROR: Unsupported Python version %PYVER%.
echo Python 3.11 is recommended for this project.
echo Accepted versions are Python 3.10 and Python 3.11 only.
echo Python 3.12 and newer are not supported for this setup.
exit /b 1

:python_ok
echo Python version accepted.

echo Checking NVIDIA GPU with nvidia-smi...
where nvidia-smi >nul 2>nul
if errorlevel 1 (
    echo WARNING: nvidia-smi was not found.
    echo CUDA version cannot be detected. Defaulting to PyTorch CUDA 12.1 wheels.
    set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121"
    goto cuda_mapping_done
)

for /f "tokens=* delims=" %%G in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>nul') do (
    if not defined GPU_NAME set "GPU_NAME=%%G"
)
if defined GPU_NAME (
    echo Detected GPU: %GPU_NAME%
) else (
    echo WARNING: nvidia-smi is available, but GPU name could not be read.
)

for /f "tokens=* delims=" %%C in ('nvidia-smi 2^>nul ^| powershell -NoProfile -Command "$input | ForEach-Object { if ($_ -match 'CUDA Version:\s*([0-9]+(?:\.[0-9]+)?)') { $Matches[1]; break } }"') do (
    if not defined CUDA_VERSION set "CUDA_VERSION=%%C"
)

if not defined CUDA_VERSION (
    echo WARNING: CUDA version could not be detected from nvidia-smi.
    echo Defaulting to PyTorch CUDA 12.1 wheels.
    set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121"
    goto cuda_mapping_done
)

echo Detected CUDA version from nvidia-smi: %CUDA_VERSION%
for /f "tokens=* delims=" %%U in ('python -c "from decimal import Decimal; import os, sys; cuda=Decimal(os.environ['CUDA_VERSION']); print('https://download.pytorch.org/whl/cu124' if cuda >= Decimal('12.4') else 'https://download.pytorch.org/whl/cu121' if cuda >= Decimal('12.1') else 'https://download.pytorch.org/whl/cu118' if cuda >= Decimal('11.8') else 'UNSUPPORTED')"') do set "TORCH_INDEX_URL=%%U"

if "%TORCH_INDEX_URL%"=="UNSUPPORTED" (
    echo ERROR: CUDA %CUDA_VERSION% is older than 11.8.
    echo GPU setup requires CUDA 11.8 or newer as reported by nvidia-smi.
    echo Use install_cpu.bat or update your NVIDIA driver.
    exit /b 1
)

:cuda_mapping_done
echo PyTorch wheel index: %TORCH_INDEX_URL%

if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo Virtual environment already exists. Reusing it.
)

if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment Python was not found after setup.
    echo Expected: "%VENV_PYTHON%"
    exit /b 1
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

echo Upgrading pip, setuptools, and wheel...
"%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel --no-input
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip, setuptools, and wheel.
    exit /b 1
)

echo Installing GPU-compatible PyTorch packages...
"%VENV_PYTHON%" -m pip install torch torchvision torchaudio --index-url "%TORCH_INDEX_URL%" --no-input
if errorlevel 1 (
    echo ERROR: PyTorch GPU installation failed.
    echo Try rerunning install_gpu.bat, or use install_cpu.bat for CPU setup.
    exit /b 1
)

echo Installing remaining project dependencies from requirements.txt...
"%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS%" --no-input
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    echo Check your internet connection, then rerun install_gpu.bat.
    exit /b 1
)

echo Verifying PyTorch CUDA availability...
"%VENV_PYTHON%" -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda); raise SystemExit(0 if torch.cuda.is_available() else 1)"
if errorlevel 1 (
    echo ERROR: PyTorch installed, but torch.cuda.is_available() is false.
    echo GPU setup did not succeed. Try updating your NVIDIA driver or use install_cpu.bat.
    exit /b 1
)

echo Verifying Python package imports...
"%VENV_PYTHON%" -c "import faster_whisper; print('faster_whisper import OK')"
if errorlevel 1 (
    echo ERROR: faster_whisper import failed.
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_gpu.bat.
    exit /b 1
)

"%VENV_PYTHON%" -c "import ctranslate2; print(ctranslate2.__version__)"
if errorlevel 1 (
    echo ERROR: ctranslate2 import failed.
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_gpu.bat.
    exit /b 1
)

"%VENV_PYTHON%" -c "import tqdm; print('tqdm import OK')"
if errorlevel 1 (
    echo ERROR: tqdm import failed.
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_gpu.bat.
    exit /b 1
)

"%VENV_PYTHON%" -c "import colorama; print('colorama import OK')"
if errorlevel 1 (
    echo ERROR: colorama import failed.
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_gpu.bat.
    exit /b 1
)

echo.
echo GPU setup completed successfully.
echo Next steps:
echo 1. Run download_ffmpeg.bat when it is available.
echo 2. Run download_models.bat when it is available.
echo 3. Run run_subtitles.bat when setup is complete.
echo.
exit /b 0
