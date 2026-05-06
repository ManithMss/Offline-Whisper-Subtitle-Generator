# Offline Whisper Subtitle Generator

A fully local Windows project for generating English `.srt` subtitles from video
and audio files after FFmpeg, Faster-Whisper, and the selected models have been
installed through the project setup scripts.

This is the Phase 1 foundation skeleton. FFmpeg downloading, dependency
installation, media scanning, Whisper transcription, subtitle formatting, and
runtime batch scripts are intentionally added in later phases.

## Project Layout

Place the project on a drive with enough free space, for example:

```text
D:\WhisperSubtitleProject\
```

The foundation script creates these local folders when run:

```text
ffmpeg\bin\
models\small\
models\medium\
cache\
logs\
temp\
output_subtitles\
processed\
videos\japanese\
videos\russian\
videos\english\
videos\hindi\
videos\auto_detect\
```

## Configuration

`config.json` contains the default project settings. The FFmpeg timeout is:

```json
"ffmpeg_timeout_seconds": null
```

`null` means unlimited processing time, which is required for long movies and
large transport stream files.

## Phase Status

Phase 1 creates the project foundation only. No FFmpeg or Whisper processing is
implemented yet.
