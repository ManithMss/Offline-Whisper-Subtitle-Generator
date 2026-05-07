@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Add local Python 3.11 to PATH priority
set "ROOT=%~dp0"
set "PATH=%ROOT%python 3.11;%ROOT%python 3.11\Scripts;%PATH%"
set "VENV_DIR=%ROOT%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "SCRIPT=%ROOT%subtitle_generator.py"
set "FFMPEG_EXE=%ROOT%ffmpeg\bin\ffmpeg.exe"
set "FFPROBE_EXE=%ROOT%ffmpeg\bin\ffprobe.exe"
set "DRY_RUN="
set "OVERWRITE="
set "INPUT_FILE="
set "DEVICE=cpu"
set "MODEL=small"

echo.
echo Offline Whisper Subtitle Generator
echo Project root: "%ROOT%"
echo.

if not exist "%VENV_DIR%" (
    echo Dependencies not installed. Please run install_cpu.bat or install_gpu.bat first.
    goto finish_fail
)

if not exist "%VENV_PYTHON%" (
    echo Dependencies not installed. Please run install_cpu.bat or install_gpu.bat first.
    echo Missing virtual environment Python:
    echo "%VENV_PYTHON%"
    goto finish_fail
)

if not exist "%SCRIPT%" (
    echo ERROR: subtitle_generator.py was not found.
    echo Expected: "%SCRIPT%"
    goto finish_fail
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

if not exist "%ROOT%cache" mkdir "%ROOT%cache"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
if not exist "%ROOT%temp" mkdir "%ROOT%temp"
if not exist "%ROOT%output_subtitles" mkdir "%ROOT%output_subtitles"
if not exist "%ROOT%processed" mkdir "%ROOT%processed"

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat.
    goto finish_fail
)

echo Verifying Python package imports...
"%VENV_PYTHON%" -c "import faster_whisper"
if errorlevel 1 (
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat.
    goto finish_fail
)

"%VENV_PYTHON%" -c "import ctranslate2"
if errorlevel 1 (
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat.
    goto finish_fail
)

"%VENV_PYTHON%" -c "import tqdm"
if errorlevel 1 (
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat.
    goto finish_fail
)

"%VENV_PYTHON%" -c "import colorama"
if errorlevel 1 (
    echo Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat.
    goto finish_fail
)

if not exist "%FFMPEG_EXE%" (
    echo FFmpeg not found. Please run download_ffmpeg.bat first.
    goto finish_fail
)

if not exist "%FFPROBE_EXE%" (
    echo FFmpeg not found. Please run download_ffmpeg.bat first.
    goto finish_fail
)

echo Verifying model files...
call :verify_model "small"
if errorlevel 1 (
    echo Whisper models not found. Please run download_models.bat first.
    goto finish_fail
)

call :verify_model "medium"
if errorlevel 1 (
    echo Whisper models not found. Please run download_models.bat first.
    goto finish_fail
)

echo Detecting CUDA capability...
for /f "tokens=*" %%C in ('"%VENV_PYTHON%" -c "import ctranslate2; print('cuda' if ctranslate2.get_cuda_device_count() > 0 else 'cpu')" 2^>nul') do set "CUDA_STATUS=%%C"
if /i "%CUDA_STATUS%"=="cuda" (
    echo CUDA GPU detected. Using GPU acceleration.
    set "DEVICE=cuda"
    set "MODEL=medium"
) else (
    echo No CUDA GPU detected. Using CPU processing.
    set "DEVICE=cpu"
    set "MODEL=small"
)

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--dry-run" (
    set "DRY_RUN=--dry-run"
    shift
    goto parse_args
)
if /i "%~1"=="--overwrite" (
    set "OVERWRITE=--overwrite"
    shift
    goto parse_args
)
if not defined INPUT_FILE (
    set "INPUT_FILE=%~1"
    shift
    goto parse_args
)
echo ERROR: Unexpected extra argument: "%~1"
goto finish_fail

:args_done
echo.
echo Starting subtitle generation...
echo Device: %DEVICE%
echo Model: %MODEL%
if defined DRY_RUN echo Mode: dry-run
if defined INPUT_FILE echo Input: "%INPUT_FILE%"
echo.

if defined INPUT_FILE (
    "%VENV_PYTHON%" "%SCRIPT%" %DRY_RUN% %OVERWRITE% --device "%DEVICE%" --model "%MODEL%" --input "%INPUT_FILE%"
) else (
    "%VENV_PYTHON%" "%SCRIPT%" %DRY_RUN% %OVERWRITE% --device "%DEVICE%" --model "%MODEL%"
)

set "RUN_EXIT=%ERRORLEVEL%"
echo.
if "%RUN_EXIT%"=="0" (
    echo Subtitle run finished.
) else (
    echo Subtitle run finished with errors. Check logs\error.log for details.
)
goto finish

:verify_model
set "MODEL_NAME=%~1"
set "MODEL_DIR=%ROOT%models\%MODEL_NAME%"
if not exist "%MODEL_DIR%\model.bin" exit /b 1
if not exist "%MODEL_DIR%\config.json" exit /b 1
if not exist "%MODEL_DIR%\tokenizer.json" exit /b 1
if not exist "%MODEL_DIR%\vocabulary.txt" exit /b 1
exit /b 0

:finish_fail
set "RUN_EXIT=1"

:finish
echo.
pause
exit /b %RUN_EXIT%
