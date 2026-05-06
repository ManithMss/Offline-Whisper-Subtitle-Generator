You are building a fully local Windows-based AI subtitle generator project.

The system must generate English .srt subtitle files from dubbed videos/audio files using Faster-Whisper and FFmpeg.

IMPORTANT RULES:
- Do NOT install large dependencies inside the AI IDE/tool.
- Do NOT run pip installs automatically during code generation.
- Only generate project files and scripts.
- Large installs/downloads must happen later through BAT files manually run in Windows CMD/PowerShell.
- Setup scripts must be unattended after launch, meaning no repeated confirmations.
- Python may be installed on C drive.
- All project files, models, cache, logs, temp files, FFmpeg binaries, outputs, and downloads must stay inside ProjectRoot, preferably on D drive.
- Always generate English subtitles, regardless of original spoken language.
- Use Whisper translation mode: task="translate".
- Use Faster-Whisper.
- Do not use OpenAI API.
- Do not use any paid/cloud subtitle API.
- Everything must work locally/offline after dependencies, FFmpeg, and models are downloaded.

==================================================
FINAL PROJECT STRUCTURE
==================================================

Required final folder structure:

ProjectRoot/
│
├── run_subtitles.bat
├── install_cpu.bat
├── install_gpu.bat
├── download_models.bat
├── download_ffmpeg.bat
├── subtitle_generator.py
├── config.json
├── requirements.txt
├── README.md
│
├── ffmpeg/
│   └── bin/
│       ├── ffmpeg.exe
│       └── ffprobe.exe
│
├── models/
│   ├── small/
│   └── medium/
│
├── cache/
├── logs/
├── temp/
├── output_subtitles/
│
├── processed/
│   └── processed_files.json
│
└── videos/
    ├── japanese/
    ├── russian/
    ├── english/
    ├── hindi/
    └── auto_detect/

All folders must be created automatically by installer/setup logic if missing.

==================================================
SUPPORTED INPUT FORMATS
==================================================

Support these extensions:

.mp4
.mkv
.avi
.mov
.ts
.mp3
.wav
.m4a
.flac

The system must support:
- video files
- audio-only files
- large .ts transport stream files
- long movies
- anime episodes
- podcasts/audio recordings

==================================================
LANGUAGE FOLDER LOGIC
==================================================

videos/japanese/
- assume Japanese speech
- use language code ja

videos/russian/
- assume Russian speech
- use language code ru

videos/hindi/
- assume Hindi speech
- use language code hi

videos/english/
- assume English speech
- use language code en

videos/auto_detect/
- do not pass language
- let Whisper auto-detect

All outputs must still be English .srt files.

==================================================
OUTPUT RULES
==================================================

Output subtitles into matching subfolders:

videos/japanese/anime01.mkv
-> output_subtitles/japanese/anime01.en.srt

videos/russian/movie.ts
-> output_subtitles/russian/movie.en.srt

videos/english/podcast.mp3
-> output_subtitles/english/podcast.en.srt

videos/japanese/season1/episode01.mkv
-> output_subtitles/japanese/season1/episode01.en.srt

Rules:
- preserve original filename
- preserve nested folder structure
- create output parent directories automatically using mkdir(parents=True, exist_ok=True)
- UTF-8 encoding
- valid SRT timestamps
- English subtitles only
- avoid overwriting existing subtitles unless overwrite_existing=true in config.json or --overwrite is passed

==================================================
MODEL RULES
==================================================

Use Faster-Whisper models only.

Only support/download:
- small
- medium

Rules:
- CPU mode uses small
- GPU mode uses medium
- do not use tiny
- do not use base
- do not use large-v3
- do not download any other models unless the user manually changes the project later

Model folders:

models/small/
models/medium/

Explicit Hugging Face model IDs:
- Systran/faster-whisper-small
- Systran/faster-whisper-medium

Required model file verification for each model folder:
- model.bin
- config.json
- tokenizer.json
- vocabulary.txt

If any required file is missing:
- treat model as incomplete
- do not attempt subtitle generation
- show: "Model files are incomplete. Please rerun download_models.bat."

Runtime must never download models.

==================================================
GPU / CPU BEHAVIOR
==================================================

The system must automatically detect CUDA capability.

If CUDA GPU exists:
- display: "CUDA GPU detected. Using GPU acceleration."
- use device="cuda"
- use model="medium"
- preferred compute_type="float16"

If no CUDA GPU exists:
- display: "No CUDA GPU detected. Using CPU processing."
- use device="cpu"
- use model="small"
- compute_type="int8"

User must not manually edit Python code to switch CPU/GPU.

Python must verify actual CUDA availability; do not only trust BAT detection.

==================================================
GPU FAILURE FALLBACK
==================================================

If GPU processing fails because of:
- CUDA error
- VRAM error
- out-of-memory error
- CTranslate2 CUDA failure

Then retry safely:
1. Retry GPU with safer compute_type such as int8_float16.
2. If still failing, fall back to CPU small model.
3. Continue processing remaining files.

Do not crash the full batch because one file fails.

==================================================
STORAGE / CACHE RULES
==================================================

Redirect these environment variables locally into ProjectRoot:

HF_HOME
HUGGINGFACE_HUB_CACHE
TRANSFORMERS_CACHE
TORCH_HOME
XDG_CACHE_HOME
TEMP
TMP
PIP_CACHE_DIR

Do not pollute:
- AppData
- default Hugging Face cache
- default Torch cache
- C drive temp folders
- user cache folders

Python itself may be installed on C drive, but heavy project files must stay local to ProjectRoot.

==================================================
FFMPEG RULES
==================================================

Use only local FFmpeg binaries:

ProjectRoot/ffmpeg/bin/ffmpeg.exe
ProjectRoot/ffmpeg/bin/ffprobe.exe

Do not require global FFmpeg installation.

download_ffmpeg.bat must exist.

download_ffmpeg.bat requirements:
- create ffmpeg/ and ffmpeg/bin/
- check if ffmpeg.exe and ffprobe.exe already exist
- if missing, download FFmpeg automatically
- primary source URL:
  https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
- fallback source URL:
  https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
- extract only ffmpeg.exe and ffprobe.exe into ffmpeg/bin/
- use PowerShell Expand-Archive for extraction
- search recursively inside extracted folder for ffmpeg.exe and ffprobe.exe
- do NOT hardcode the internal ZIP folder path as it changes with each release
- verify:
  ffmpeg.exe -version
  ffprobe.exe -version
- skip download if both already exist and verify successfully
- be safe to rerun
- be unattended
- no repeated user confirmations
- if both downloads fail, print clear manual setup instructions

README.md must also explain manual FFmpeg setup:
- download FFmpeg from gyan.dev or BtbN/FFmpeg-Builds
- copy ffmpeg.exe and ffprobe.exe into ffmpeg/bin/

Before Whisper processing:
- extract/convert input audio to 16kHz mono WAV
- store temp audio in ProjectRoot/temp/
- clean temp files after successful processing if config allows

FFmpeg subprocess must:
- use subprocess.run with list arguments
- not use unsafe shell=True unless absolutely necessary
- use timeout from config.json ffmpeg_timeout_seconds
- if ffmpeg_timeout_seconds is null, pass timeout=None which means wait forever
- only kill process if ffmpeg_timeout_seconds is a positive integer and it expires
- log timeout error
- continue batch

After FFmpeg extracts/converts audio:
- validate WAV exists
- validate file size > 0
- validate ffprobe can read duration
- validate duration > 0 seconds
- if validation fails, log error and skip that media file

==================================================
PYTHON VERSION RULES
==================================================

Target Python version:
- Python 3.11 is recommended and preferred.

Installer behavior:
- detect Python version before creating .venv
- use: python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')"
- do NOT parse the human-readable python --version string
- accept Python 3.10 and 3.11 as safe targets
- reject Python 3.12+ with clear message
- reject very old Python versions with clear message
- if unsupported Python detected, stop before installing dependencies
- print: "Python 3.11 is recommended for this project."

Do not silently continue with unsupported Python.

==================================================
INSTALLATION DESIGN
==================================================

Very important:
Large dependencies must NOT be installed automatically during normal subtitle generation.

run_subtitles.bat must NOT install:
- torch
- faster-whisper
- ctranslate2
- models
- FFmpeg

Instead, it must check and show helpful messages.

If .venv missing:
"Dependencies not installed. Please run install_cpu.bat or install_gpu.bat first."

If .venv exists but imports fail:
"Virtual environment exists but dependencies are incomplete. Please rerun install_cpu.bat or install_gpu.bat."

If models missing:
"Whisper models not found. Please run download_models.bat first."

If FFmpeg missing:
"FFmpeg not found. Please run download_ffmpeg.bat first."

==================================================
UNATTENDED SETUP REQUIREMENT
==================================================

The user wants to run setup and continue doing other work.

Installer scripts must:
- create folders automatically
- create .venv automatically
- install dependencies automatically
- avoid repeated confirmations
- avoid Y/N prompts
- avoid interactive package prompts
- be resumable/idempotent
- skip existing folders/files/packages where possible
- continue unattended after launch
- be safe to rerun

Do not require the user to click "Allow" repeatedly inside an IDE.

All heavy installs must happen externally through Windows CMD/PowerShell by running BAT files.

==================================================
INSTALL_CPU.BAT REQUIREMENTS
==================================================

install_cpu.bat must:
- use "%~dp0" safely
- quote all paths
- handle ProjectRoot paths with spaces
- create required folder structure automatically
- validate Python version before install using:
  python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')"
- recommend Python 3.11
- accept 3.10 and 3.11 only
- reject 3.12+ with clear stop message
- create .venv if missing
- activate .venv
- set local cache/temp environment variables
- upgrade pip, setuptools, wheel
- install CPU-compatible dependencies
- avoid CUDA packages
- install requirements.txt
- verify imports:
  faster_whisper
  ctranslate2
  tqdm
  colorama
- verify ctranslate2 version using:
  python -c "import ctranslate2; print(ctranslate2.__version__)"
- be unattended
- no Y/N prompts
- safe to rerun

==================================================
INSTALL_GPU.BAT REQUIREMENTS
==================================================

install_gpu.bat must:
- use "%~dp0" safely
- quote all paths
- handle ProjectRoot paths with spaces
- create required folder structure automatically
- validate Python version before install using:
  python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')"
- recommend Python 3.11
- accept 3.10 and 3.11 only
- reject 3.12+ with clear stop message
- create .venv if missing
- activate .venv
- set local cache/temp environment variables
- upgrade pip, setuptools, wheel
- check nvidia-smi
- display detected GPU name if possible
- display detected CUDA version from nvidia-smi if possible
- install GPU-compatible dependencies
- install PyTorch using a defined CUDA wheel strategy
- verify after install:
  python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda)"
- verify ctranslate2 import/version
- if torch.cuda.is_available() is false, show clear warning/failure
- do not silently claim GPU setup succeeded
- advise using install_cpu.bat if GPU setup fails
- be unattended
- no Y/N prompts
- safe to rerun

PyTorch CUDA wheel selection:
1. Run nvidia-smi if available.
2. Read reported CUDA version.
3. Map detected CUDA version to PyTorch wheel index:

CUDA 12.4 or newer:
  https://download.pytorch.org/whl/cu124

CUDA 12.1 to 12.3:
  https://download.pytorch.org/whl/cu121

CUDA 11.8 to 12.0:
  https://download.pytorch.org/whl/cu118

If CUDA version cannot be detected:
- default to cu121
- print a warning explaining the assumption

If CUDA version is older than 11.8:
- stop GPU installer
- suggest install_cpu.bat or updating NVIDIA driver

Important:
Do not assume the system CUDA toolkit alone guarantees PyTorch compatibility.
Verify actual Python CUDA availability after installation.

==================================================
CTRANSLATE2 ROBUSTNESS
==================================================

The installer must verify ctranslate2 after installation.

Use:
python -c "import ctranslate2; print(ctranslate2.__version__)"

If ctranslate2 import fails:
- show clear error
- stop installer
- suggest rerunning installer
- do not pretend setup succeeded

requirements.txt should avoid careless unpinned dependency chaos.
Use sensible version constraints where appropriate.

==================================================
DOWNLOAD_MODELS.BAT REQUIREMENTS
==================================================

download_models.bat must:
- use "%~dp0" safely
- quote all paths
- activate .venv
- set local model/cache variables
- download only:
  Systran/faster-whisper-small
  Systran/faster-whisper-medium
- use huggingface_hub.snapshot_download() via inline Python script
- do NOT use huggingface-cli
- save to:
  models/small/
  models/medium/
- skip already complete models
- verify required files:
  model.bin
  config.json
  tokenizer.json
  vocabulary.txt
- handle 401/403 authorization errors clearly
- handle network failure clearly
- handle partial downloads
- be resumable/idempotent
- no browser login if not required
- no confirmations

If model access fails:
"Model download failed. Check internet connection or Hugging Face access. You may need to manually download the model."

Do not download models during subtitle generation.

==================================================
RUN_SUBTITLES.BAT REQUIREMENTS
==================================================

run_subtitles.bat must:
- use "%~dp0" safely
- quote all paths
- handle ProjectRoot paths with spaces
- verify .venv exists
- verify .venv Python exists
- activate .venv
- set local cache/temp variables
- verify ffmpeg/bin/ffmpeg.exe exists
- verify ffmpeg/bin/ffprobe.exe exists
- verify required packages are importable:
  faster_whisper
  ctranslate2
  tqdm
  colorama
- verify models/small and models/medium exist and contain required files
- detect CUDA GPU if possible
- display:
  "CUDA GPU detected. Using GPU acceleration."
  or
  "No CUDA GPU detected. Using CPU processing."
- if CUDA exists, pass/use GPU mode and medium model
- if CUDA does not exist, pass/use CPU mode and small model
- do NOT install dependencies
- do NOT download models
- do NOT download FFmpeg
- pause at end so errors remain visible

==================================================
DRAG-DROP AND ARGUMENT HANDLING
==================================================

run_subtitles.bat and subtitle_generator.py must support these cases:

Case 1:
run_subtitles.bat
Behavior:
- normal batch processing

Case 2:
run_subtitles.bat --dry-run
Behavior:
- dry-run scan of all videos folders

Case 3:
drag a media file onto run_subtitles.bat
Behavior:
- process only that file

Case 4:
run_subtitles.bat --dry-run "D:\Videos\movie file.mkv"
Behavior:
- dry-run only that file

Case 5:
run_subtitles.bat "D:\Videos\movie file.mkv" --dry-run
Behavior:
- dry-run only that file

Argument parsing requirements:
- BAT must detect whether an argument is --dry-run or a file path
- BAT must support both --dry-run and input file together
- BAT must quote all paths
- Python argparse must support:
  --dry-run
  --input "path"
  --overwrite
  --device cpu/cuda
  --model small/medium

Do not assume %1 is always the file path.
Do not assume %1 is always --dry-run.
Use "%~1" safely.

==================================================
DRY-RUN MODE
==================================================

Add dry-run mode.

Python:
--dry-run

BAT:
run_subtitles.bat --dry-run

Dry run must:
- scan files
- show what would be processed
- show intended output paths
- show skipped existing outputs
- not run FFmpeg
- not run Whisper
- not write subtitles
- not update processed_files.json

==================================================
CLI CONFIG OVERRIDES
==================================================

subtitle_generator.py must support:

--overwrite
--dry-run
--device cpu
--device cuda
--model small
--model medium
--input "path"

CLI overrides should override config.json for that run only.

==================================================
TEMP FILE COLLISION AVOIDANCE
==================================================

Temporary WAV filenames must be unique.

Do not use only input_file.stem.

Use a safe unique strategy:
- hash of absolute input path
- file modified time
- file size
- process id or timestamp

Example:
temp/audio_<hash>.wav

Two files with the same name in different folders must never overwrite each other's temp WAV.

==================================================
SUBTITLE QUALITY
==================================================

Generate clean readable SRT files.

Formatting rules:
- UTF-8 .srt
- proper SRT index numbers
- proper timestamps:
  HH:MM:SS,mmm --> HH:MM:SS,mmm
- max 42 characters per line
- max 2 lines per subtitle
- avoid very long subtitle blocks
- preserve timing accuracy
- use beam search
- make subtitle text readable for movies/anime

SRT edge cases:
- skip empty text segments
- skip zero-duration segments
- ensure end time > start time
- clamp tiny overlaps safely
- avoid duplicate blank cues
- remove excessive whitespace
- sanitize segment text

==================================================
SRT METADATA RULE
==================================================

Do NOT write NOTE blocks inside .srt files by default.

Default config:
"write_srt_metadata_note": false

Reason:
Standard SRT does not reliably support NOTE blocks. Some players may display metadata as subtitle text.

Preferred default:
- store source file, language, model, and device info in logs/success.log
- do not insert metadata into .srt files

If metadata is manually enabled:
- write comment-style lines starting with #
- warn in README that some players may display those lines

==================================================
FASTER-WHISPER DETECTED LANGUAGE
==================================================

After transcription, capture detected_language from the Faster-Whisper info object:

segments, info = model.transcribe(audio_path, task="translate", ...)
detected_language = info.language

Store detected_language in:
- the processed registry entry in processed_files.json
- logs/success.log

==================================================
RESUME SUPPORT
==================================================

Use:

processed/processed_files.json

It must track completed files.

Track:
- input path
- file size
- modified time
- output path
- device used
- model used
- detected language
- completion time

Requirements:
- skip already processed files if unchanged
- if file changed since last processing, process again
- resume after crash/shutdown
- rerunning must not duplicate work
- safe JSON read/write

Atomic write required:
1. write updated JSON to processed_files.tmp
2. flush and close file
3. replace original using os.replace()

If processed_files.json is corrupt:
- rename it to processed_files.corrupt.<timestamp>.json
- create a new clean processed_files.json
- log the recovery
- do not allow corrupt JSON to permanently crash the app

==================================================
LOGGING
==================================================

Create and use:

logs/success.log
logs/error.log
logs/skipped.log

Use log rotation:
- max log size: 5 MB
- backup count: 3

Use Python RotatingFileHandler or equivalent.

Log success:
- input path
- output path
- language
- detected language
- device
- model
- duration

Log skipped:
- input path
- reason

Log error:
- input path
- error details
- traceback if useful

Also log:
- FFmpeg timeout errors
- model loading errors
- config recovery events
- processed_files.json recovery events
- total runtime summary

The app must continue processing remaining files after errors.

==================================================
CONFIG.JSON REQUIREMENTS
==================================================

Generate config.json with these defaults:

{
  "overwrite_existing": false,
  "recursive_scan": true,
  "cleanup_temp": true,
  "beam_size": 5,
  "max_chars_per_line": 42,
  "max_lines_per_subtitle": 2,
  "audio_sample_rate": 16000,
  "audio_channels": 1,
  "translate_to_english": true,
  "log_success": true,
  "log_errors": true,
  "log_skipped": true,
  "ffmpeg_timeout_seconds": null,
  "log_max_bytes": 5242880,
  "log_backup_count": 3,
  "write_srt_metadata_note": false
}

IMPORTANT: ffmpeg_timeout_seconds must be null by default, not 1800.
null means unlimited wait time. This is required for slow connections and large files.

config.json must be validated on load.

Validation rules:
- beam_size must be int >= 1
- max_chars_per_line must be int >= 10
- max_lines_per_subtitle must be int >= 1
- overwrite_existing must be boolean
- recursive_scan must be boolean
- cleanup_temp must be boolean
- ffmpeg_timeout_seconds must be a positive integer OR null
- null means unlimited, this is valid and expected
- 0 or negative number is invalid
- log_max_bytes must be positive integer
- log_backup_count must be non-negative integer
- write_srt_metadata_note must be boolean

If config.json is missing:
- recreate it with defaults

If config.json is corrupt JSON:
- rename to config.corrupt.<timestamp>.json
- recreate default config
- log warning

If config has invalid values:
- use safe defaults or show clear validation error
- do not crash with a cryptic traceback

==================================================
PYTHON SCRIPT REQUIREMENTS
==================================================

subtitle_generator.py must:
- use pathlib
- use argparse
- use subprocess with list arguments
- use json
- use logging with rotation
- use tqdm
- use colorama
- use faster_whisper
- load and validate config.json
- create missing folders if needed
- set local cache/temp environment variables
- recursively scan input folders
- support single-file input mode
- support dry-run mode
- map folder names to languages
- use auto-detect for auto_detect folder
- verify FFmpeg exists
- extract audio with local FFmpeg
- pass timeout=config["ffmpeg_timeout_seconds"] to subprocess.run directly
- timeout=None means wait forever, do not add special handling for None
- validate extracted WAV
- run Faster-Whisper with task="translate"
- capture detected_language from transcription info object
- generate .srt files
- apply clean subtitle formatting
- maintain processed_files.json with atomic writes
- log success/skipped/errors including detected_language
- handle failures gracefully
- continue batch after errors
- show progress bars and counters

==================================================
TERMINAL UI
==================================================

Show:
- File X of Y
- current file
- selected device
- selected model
- output path
- processed count
- skipped count
- failed count
- total runtime at end

Final summary format:

Processed: X
Skipped: X
Failed: X
Total Runtime: HH:MM:SS
Output Folder: ...
Device Used: GPU/CPU
Model Used: small/medium

==================================================
REQUIREMENTS.TXT
==================================================

Include only needed packages.

Prefer:
- faster-whisper
- ctranslate2
- tqdm
- colorama
- huggingface_hub

Do not force unnecessary bloated packages unless required.

Torch should be handled carefully in installer scripts, especially GPU/CPU differences.

==================================================
README REQUIREMENTS
==================================================

README.md must be beginner-friendly.

Explain:

1. Put project on D drive:
   D:\WhisperSubtitleProject\

2. Download FFmpeg:
   download_ffmpeg.bat

3. Install dependencies:
   install_gpu.bat
   or
   install_cpu.bat

4. Download models:
   download_models.bat

5. Add media files to:
   videos/japanese/
   videos/russian/
   videos/hindi/
   videos/english/
   videos/auto_detect/

6. Run:
   run_subtitles.bat

7. Find subtitles in:
   output_subtitles/

Also explain:
- drag-and-drop mode
- dry-run mode
- overwrite mode
- config.json editing
- missing FFmpeg
- missing models
- Python version issue
- no CUDA detected
- GPU out of memory
- dependency install failed
- corrupted video/audio
- subtitles already exist
- how to rerun safely

==================================================
FINAL ACCEPTANCE CHECKLIST
==================================================

Before finishing, verify:
- download_ffmpeg.bat exists
- FFmpeg primary and fallback sources are explicit
- FFmpeg extraction uses Expand-Archive with recursive search
- README explains FFmpeg setup
- Python version check uses python -c not python --version
- Python version check exists in both installers
- .venv partial install detection exists
- ctranslate2 import verification exists
- faster_whisper import verification exists
- GPU install verifies torch.cuda.is_available()
- PyTorch CUDA wheel index mapping exists
- explicit model IDs are used
- download_models.bat uses snapshot_download not huggingface-cli
- small and medium only
- required model files are verified
- no runtime model downloads
- no runtime dependency installs
- all BAT paths are quoted
- ProjectRoot with spaces works
- drag-drop quoted path works
- dry-run + input file works
- Unicode filenames supported
- .mp3 works
- .ts works
- .mkv works
- nested folders work
- ffmpeg_timeout_seconds is null by default
- timeout=None passed to subprocess means unlimited wait
- extracted WAV validation works
- output parent dirs are created
- temp WAV filenames are unique
- detected_language captured from Whisper info object
- detected_language stored in processed registry and success log
- processed_files.json atomic write implemented
- corrupt processed_files.json recovery implemented
- config validation exists and accepts null for ffmpeg_timeout_seconds
- corrupt config recovery exists
- log rotation exists
- SRT NOTE metadata is disabled by default
- empty/zero-duration segments are skipped
- overlapping timestamps are handled
- File X of Y progress shown
- final summary includes total runtime

For every phase:
- Do only the requested phase.
- Do not jump ahead.
- Do not remove existing requirements.
- After coding, list changed files.
- Provide a small test checklist.
