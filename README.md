# Offline Whisper Subtitle Generator

Complete step-by-step guide to set up and run the project on Windows so any
user can install prerequisites, download models and FFmpeg, and produce
English `.srt` subtitle files without extra guidance.

Supported OS: Windows 10 / 11 (PowerShell or CMD).

IMPORTANT: run BAT files from an interactive Windows CMD or PowerShell window
with normal user permissions. Do not run installs inside an IDE terminal
unless you know it inherits the correct PATH and permissions.

Project location
----------------
Place the project where you have disk space (prefer D:). Example:

```
D:\WhisperSubtitleProject\
```

Everything large (models, FFmpeg, cache, temp, outputs, logs) stays inside
the project folder. Python itself may be installed on `C:`.

Quick command overview
----------------------
- `prerequisites\install_cpu.bat` — install CPU dependencies into `.venv`.
- `prerequisites\install_gpu.bat` — install GPU dependencies into `.venv`.
- `prerequisites\download_models.bat` — download Faster-Whisper small/medium.
- `prerequisites\download_ffmpeg.bat` — download and install FFmpeg locally.
- `run_subtitles.bat` — run subtitle generation (no installs or downloads).
- `menu.bat` — interactive menu to call the prerequisite scripts.

Step-by-step setup (first run)
------------------------------
1) Verify you have a working Python 3.10 or 3.11 on PATH. To check:

```powershell
python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')"
```

Acceptable outputs: `3.10` or `3.11`. If you get `3.12` or newer, install
Python 3.11 and ensure it is used by the installers.

2) Open a new PowerShell or CMD in the project root (where this README is).

3) Run the interactive helper menu (recommended):

```powershell
menu.bat
```

Use the menu options to run any single prerequisite or the "Run ALL"
sequence. The menu only calls the scripts in `prerequisites\` — it does not
perform installs itself.

Manual single-step commands (no menu)
------------------------------------
If you prefer to run steps manually in order, run these commands from the
project root (PowerShell or CMD):

```powershell
prerequisites\download_ffmpeg.bat
prerequisites\install_cpu.bat    # or prerequisites\install_gpu.bat
prerequisites\download_models.bat
```

Notes:
- Use `install_gpu.bat` only if you have an NVIDIA GPU and the installer
   detects a supported CUDA version. If GPU install fails, use `install_cpu.bat`.
- `download_models.bat` downloads only `Systran/faster-whisper-small` and
   `Systran/faster-whisper-medium` into `models\small` and `models\medium`.

How to run the subtitle generator
---------------------------------
After prerequisites complete and `.venv` is present, run the main script:

```powershell
run_subtitles.bat
```

Common modes and examples:
- Dry run (scan only): `run_subtitles.bat --dry-run`
- Process a single file: `run_subtitles.bat "D:\Videos\movie file.mkv"`
- Dry run a single file: `run_subtitles.bat --dry-run "D:\Videos\movie file.mkv"`
- Overwrite existing subtitles: `run_subtitles.bat --overwrite`

Drag-and-drop: drag any media file onto `run_subtitles.bat` in Explorer to
process that single file.

What the installers do (summary)
--------------------------------
- Create `\.venv` if missing (inside project root).
- Set local cache environment variables so Hugging Face, Torch and other
   caches remain inside the project folder.
- Upgrade `pip`, `setuptools`, and `wheel` then `pip install -r requirements.txt`.
- `install_gpu.bat` attempts to detect CUDA via `nvidia-smi` and selects a
   compatible PyTorch wheel index (cu118/cu121/cu124) — it verifies `torch.cuda.is_available()`.

Where output files appear
-------------------------
- Subtitles: `output_subtitles\<lang>\...*.en.srt`
- Temporary audio: `temp\audio_<uniquehash>.wav` (cleaned up if `cleanup_temp`)
- Logs: `logs\success.log`, `logs\error.log`, `logs\skipped.log`
- Process registry: `processed\processed_files.json`

FFmpeg manual fallback
----------------------
If `download_ffmpeg.bat` cannot fetch the archive, manually download and
copy `ffmpeg.exe` and `ffprobe.exe` into `ffmpeg\bin` from one of these
sources:

- https://www.gyan.dev/ffmpeg/builds/
- https://github.com/BtbN/FFmpeg-Builds/releases

After copying, verify in PowerShell (from project root):

```powershell
.
ffmpeg\bin\ffmpeg.exe -version
ffmpeg\bin\ffprobe.exe -version
```

Configuration and tuning
------------------------
- Edit `config.json` for defaults. CLI flags override config for a single run.
- Key values:
   - `overwrite_existing` (bool)
   - `recursive_scan` (bool)
   - `cleanup_temp` (bool)
   - `beam_size` (int >= 1)
   - `max_chars_per_line` (int >= 10)
   - `max_lines_per_subtitle` (int >= 1)
   - `ffmpeg_timeout_seconds` (null = unlimited or positive integer)

Troubleshooting (quick fixes)
-----------------------------
- If `.venv` exists but imports fail: rerun the matching installer (GPU or CPU).
- If models show as incomplete, delete the partial folder and rerun
   `download_models.bat` or manually fetch via Hugging Face.
- If FFmpeg commands fail, verify `ffmpeg\bin` contains both `.exe` files and
   check `ffmpeg.exe -version`.
- Check logs in `logs\` for error details.

Advanced: force CPU or GPU for a single run
-----------------------------------------
You can override device and model per run (these override `config.json`):

```powershell
run_subtitles.bat --device cpu
run_subtitles.bat --device cuda --model medium
```

Final quick test checklist (do these to confirm a healthy setup)
----------------------------------------------------------------
1. `menu.bat` opens and option-run calls the corresponding script.
2. `prerequisites\download_ffmpeg.bat` places `ffmpeg\bin\ffmpeg.exe` and `ffmpeg\bin\ffprobe.exe`.
3. `prerequisites\install_cpu.bat` or `prerequisites\install_gpu.bat` creates `.venv` and installs packages.
4. `prerequisites\download_models.bat` populates `models\small` and `models\medium` with `model.bin`, `config.json`, `tokenizer.json`, `vocabulary.txt`.
5. `run_subtitles.bat --dry-run` lists files and planned outputs without creating subtitles.
6. Run a single small media file end-to-end; confirm `output_subtitles\<lang>\<name>.en.srt` appears and logs show success.

Changed files
-------------
- `README.md` — updated to be a complete, step-by-step setup and run guide.

If you want, I can also:
- create or update `menu.bat` in the project root to match these instructions,
   including the "Run ALL prerequisites in sequence" option, or
- prepare a short troubleshooting script to collect environment info for support.
