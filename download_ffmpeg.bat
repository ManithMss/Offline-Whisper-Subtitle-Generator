@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "FFMPEG_DIR=%ROOT%ffmpeg"
set "FFMPEG_BIN=%FFMPEG_DIR%\bin"
set "FFMPEG_EXE=%FFMPEG_BIN%\ffmpeg.exe"
set "FFPROBE_EXE=%FFMPEG_BIN%\ffprobe.exe"
set "DOWNLOAD_DIR=%ROOT%temp\ffmpeg_download"
set "ZIP_PATH=%DOWNLOAD_DIR%\ffmpeg.zip"
set "EXTRACT_DIR=%DOWNLOAD_DIR%\extract"
set "PRIMARY_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "FALLBACK_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

echo.
echo Offline Whisper Subtitle Generator - FFmpeg Download
echo Project root: "%ROOT%"
echo.

if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"
if not exist "%FFMPEG_BIN%" mkdir "%FFMPEG_BIN%"
if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

echo Checking existing FFmpeg binaries...
call :verify_ffmpeg
if not errorlevel 1 (
    echo FFmpeg is already installed and verified.
    echo "%FFMPEG_EXE%"
    echo "%FFPROBE_EXE%"
    exit /b 0
)

echo FFmpeg is missing or incomplete. Downloading local binaries...
echo.

call :download_and_extract "%PRIMARY_URL%" "primary gyan.dev source"
if not errorlevel 1 goto verify_after_download

echo.
echo Primary download failed. Trying fallback source...
call :download_and_extract "%FALLBACK_URL%" "fallback BtbN source"
if not errorlevel 1 goto verify_after_download

echo.
echo ERROR: Both FFmpeg downloads failed.
echo.
echo Manual FFmpeg setup:
echo 1. Download FFmpeg from one of these sources:
echo    %PRIMARY_URL%
echo    %FALLBACK_URL%
echo 2. Extract the ZIP manually.
echo 3. Search inside the extracted folder for ffmpeg.exe and ffprobe.exe.
echo 4. Copy both files into:
echo    "%FFMPEG_BIN%"
echo.
exit /b 1

:verify_after_download
echo.
echo Verifying downloaded FFmpeg binaries...
call :verify_ffmpeg
if errorlevel 1 (
    echo ERROR: FFmpeg files were copied, but verification failed.
    echo.
    echo Manual FFmpeg setup:
    echo 1. Download FFmpeg from gyan.dev or BtbN/FFmpeg-Builds.
    echo 2. Copy ffmpeg.exe and ffprobe.exe into:
    echo    "%FFMPEG_BIN%"
    exit /b 1
)

echo FFmpeg installed and verified successfully.
echo "%FFMPEG_EXE%"
echo "%FFPROBE_EXE%"
exit /b 0

:download_and_extract
set "SOURCE_URL=%~1"
set "SOURCE_NAME=%~2"

echo Downloading from %SOURCE_NAME%:
echo %SOURCE_URL%

powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $zip = $env:ZIP_PATH; $dir = Split-Path -Parent $zip; New-Item -ItemType Directory -Force -Path $dir | Out-Null; if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }; Invoke-WebRequest -Uri $env:SOURCE_URL -OutFile $zip -UseBasicParsing"
if errorlevel 1 (
    echo ERROR: Download failed from %SOURCE_NAME%.
    exit /b 1
)

echo Extracting ZIP with PowerShell Expand-Archive...
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $extractDir = $env:EXTRACT_DIR; if (Test-Path -LiteralPath $extractDir) { Remove-Item -LiteralPath $extractDir -Recurse -Force }; New-Item -ItemType Directory -Force -Path $extractDir | Out-Null; Expand-Archive -LiteralPath $env:ZIP_PATH -DestinationPath $extractDir -Force"
if errorlevel 1 (
    echo ERROR: ZIP extraction failed for %SOURCE_NAME%.
    exit /b 1
)

echo Searching recursively for ffmpeg.exe and ffprobe.exe...
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $extractDir = $env:EXTRACT_DIR; $ffmpegBin = $env:FFMPEG_BIN; New-Item -ItemType Directory -Force -Path $ffmpegBin | Out-Null; $ffmpeg = Get-ChildItem -Path $extractDir -Recurse -Filter 'ffmpeg.exe' -File | Select-Object -First 1; $ffprobe = Get-ChildItem -Path $extractDir -Recurse -Filter 'ffprobe.exe' -File | Select-Object -First 1; if (-not $ffmpeg) { throw 'ffmpeg.exe was not found in the extracted ZIP.' }; if (-not $ffprobe) { throw 'ffprobe.exe was not found in the extracted ZIP.' }; Copy-Item -LiteralPath $ffmpeg.FullName -Destination (Join-Path $ffmpegBin 'ffmpeg.exe') -Force; Copy-Item -LiteralPath $ffprobe.FullName -Destination (Join-Path $ffmpegBin 'ffprobe.exe') -Force"
if errorlevel 1 (
    echo ERROR: Could not locate and copy ffmpeg.exe and ffprobe.exe from %SOURCE_NAME%.
    exit /b 1
)

exit /b 0

:verify_ffmpeg
if not exist "%FFMPEG_EXE%" exit /b 1
if not exist "%FFPROBE_EXE%" exit /b 1
"%FFMPEG_EXE%" -version >nul 2>nul
if errorlevel 1 exit /b 1
"%FFPROBE_EXE%" -version >nul 2>nul
if errorlevel 1 exit /b 1
exit /b 0
