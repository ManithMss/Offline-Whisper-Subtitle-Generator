# Offline Whisper Subtitle Generator

Generate English `.srt` subtitle files locally on Windows from video and audio
files. The project uses local FFmpeg plus Faster-Whisper models. After setup,
subtitle generation runs offline and does not use OpenAI, paid APIs, or cloud
subtitle services.

## Put The Project On D Drive

Place the project somewhere with enough free space, for example:

```text
D:\WhisperSubtitleProject\
```

All project files, models, cache, logs, temporary audio, FFmpeg binaries, and
subtitle outputs stay inside this project folder. Python itself may be installed
on `C:`; the heavy files belong in the project folder.

## First-Time Setup

Run these BAT files from Windows CMD or PowerShell. Do not run package installs
inside the AI IDE.

1. Download local FFmpeg:

```bat
download_ffmpeg.bat
```

2. Install dependencies. Use GPU if you have a supported NVIDIA CUDA setup:

```bat
install_gpu.bat
```

Use CPU if you do not have CUDA, or if GPU setup fails:

```bat
install_cpu.bat
```

3. Download the Faster-Whisper models:

```bat
download_models.bat
```

Only these models are downloaded:

- `Systran/faster-whisper-small`
- `Systran/faster-whisper-medium`

## Add Media Files

Put media files into one of these folders:

```text
videos\japanese\
videos\russian\
videos\hindi\
videos\english\
videos\auto_detect\
```

Language folders tell Whisper what language to expect. `auto_detect` lets
Whisper detect the spoken language itself. Subtitles are always translated to
English.

Supported inputs:

```text
.mp4 .mkv .avi .mov .ts .mp3 .wav .m4a .flac
```

Nested folders are supported. For example:

```text
videos\japanese\season1\episode01.mkv
output_subtitles\japanese\season1\episode01.en.srt
```

## Run Subtitle Generation

Normal batch processing:

```bat
run_subtitles.bat
```

Subtitles are written to:

```text
output_subtitles\
```

Existing subtitles are skipped by default.

## Drag And Drop

Drag one media file onto `run_subtitles.bat` to process only that file.

You can also run:

```bat
run_subtitles.bat "D:\Videos\movie file.mkv"
```

## Dry Run

Dry run scans files and shows what would happen. It does not run FFmpeg, run
Whisper, write subtitles, or update `processed\processed_files.json`.

```bat
run_subtitles.bat --dry-run
run_subtitles.bat --dry-run "D:\Videos\movie file.mkv"
run_subtitles.bat "D:\Videos\movie file.mkv" --dry-run
```

## Overwrite Existing Subtitles

Use this when you want to regenerate subtitles that already exist:

```bat
run_subtitles.bat --overwrite
run_subtitles.bat --overwrite "D:\Videos\movie file.mkv"
```

You can also set this in `config.json`:

```json
"overwrite_existing": true
```

## Configuration

Edit `config.json` to change runtime behavior.

Useful settings:

- `recursive_scan`: scan nested folders under each language folder.
- `cleanup_temp`: delete temporary WAV files after successful processing.
- `beam_size`: Whisper beam search size.
- `max_chars_per_line`: default subtitle line width is `42`.
- `max_lines_per_subtitle`: default is `2`.
- `ffmpeg_timeout_seconds`: default is `null`, which means unlimited.
- `write_srt_metadata_note`: default is `false`.

Do not change `translate_to_english` unless you intentionally want to modify the
project behavior. The default is English subtitles for every input language.

## Manual FFmpeg Setup

`download_ffmpeg.bat` is the normal path. If it cannot download FFmpeg:

1. Download a Windows FFmpeg build from one of these sources:
   - `https://www.gyan.dev/ffmpeg/builds/`
   - `https://github.com/BtbN/FFmpeg-Builds/releases`
2. Extract the ZIP.
3. Copy these files into `ffmpeg\bin\`:
   - `ffmpeg.exe`
   - `ffprobe.exe`
4. Run `run_subtitles.bat` again.

The expected paths are:

```text
ffmpeg\bin\ffmpeg.exe
ffmpeg\bin\ffprobe.exe
```

## Troubleshooting

Missing FFmpeg:

```text
FFmpeg not found. Please run download_ffmpeg.bat first.
```

Run `download_ffmpeg.bat`, or use the manual FFmpeg setup above.

Missing models:

```text
Whisper models not found. Please run download_models.bat first.
```

Run `download_models.bat`. If the download fails, check internet access and
Hugging Face access, then rerun it.

Python version issue:

Use Python 3.11 if possible. Python 3.10 is accepted. Python 3.12 and newer are
rejected by the installers for this setup.

No CUDA detected:

The runner will use CPU mode and the small model. This is expected on systems
without a supported NVIDIA CUDA setup.

GPU out of memory or CUDA failure:

The Python runner retries GPU with a safer compute type, then falls back to CPU
small if needed. Check `logs\error.log` for details.

Dependency install failed:

Rerun `install_gpu.bat` or `install_cpu.bat`. If GPU setup keeps failing, use
`install_cpu.bat`.

Corrupted video or audio:

FFmpeg extraction or WAV validation may fail. The bad file is logged and the
batch continues with the next file.

Subtitles already exist:

Existing `.srt` files are skipped by default. Use `--overwrite` or set
`overwrite_existing` to `true` in `config.json`.

Rerun safely:

The project is designed to resume. Completed files are tracked in
`processed\processed_files.json`; unchanged files with existing subtitles are
skipped on the next run.

## Logs And Resume Data

Logs are written here:

```text
logs\success.log
logs\error.log
logs\skipped.log
```

Resume data is written here:

```text
processed\processed_files.json
```

If the registry or config JSON becomes corrupt, the app renames the corrupt file
with a timestamp and recreates a clean one.

## Final Test Checklist

After setup, a healthy project should pass these checks:

- `download_ffmpeg.bat` leaves `ffmpeg\bin\ffmpeg.exe` and `ffmpeg\bin\ffprobe.exe`.
- `install_cpu.bat` or `install_gpu.bat` creates `.venv`.
- `download_models.bat` fills `models\small\` and `models\medium\`.
- `run_subtitles.bat --dry-run` lists media without creating subtitles.
- Dragging one media file onto `run_subtitles.bat` processes only that file.
- `.mp3`, `.mkv`, and `.ts` inputs scan correctly.
- Nested media folders produce matching nested output folders.
- Existing subtitles are skipped unless `--overwrite` is used.
- Logs appear in `logs\`.
- Final subtitles appear in `output_subtitles\`.
