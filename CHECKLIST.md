# whisper-subs — Build Checklist

Use this file to track progress across all 8 phases.
Start each new phase prompt with:
> "Read CHECKLIST.md to see what is already done. Read SPEC.md for requirements. Then do Phase X only."

---

## Spec Fixes — Must Be Applied Exactly As Described

These are critical corrections to the spec. The AI must implement all of these.

---

### Fix 1 — download_ffmpeg.bat: ZIP extraction method

**Applies to:** Phase 2 → `download_ffmpeg.bat`

Use PowerShell `Expand-Archive` to extract the ZIP.
Search **recursively** inside the extracted folder for `ffmpeg.exe` and `ffprobe.exe`
rather than assuming a fixed internal path, because the folder name changes with each
release version (e.g. `ffmpeg-7.1-essentials_build/bin/`).

```powershell
# Correct approach — search recursively, do not hardcode path
Get-ChildItem -Path "$extractDir" -Recurse -Filter "ffmpeg.exe" | Copy-Item -Destination "$ffmpegBin"
Get-ChildItem -Path "$extractDir" -Recurse -Filter "ffprobe.exe" | Copy-Item -Destination "$ffmpegBin"
```

**Do not hardcode** a path like `ffmpeg-release-essentials\bin\ffmpeg.exe`.

---

### Fix 2 — install_cpu.bat and install_gpu.bat: Python version detection

**Applies to:** Phase 2 → `install_cpu.bat` and `install_gpu.bat`

Detect Python version using this command — do **not** parse the human-readable
`python --version` string (it is fragile in BAT):

```bat
for /f "tokens=*" %%V in ('python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')"') do set PYVER=%%V
```

Then compare `%PYVER%` against `3.10` and `3.11` as accepted versions.
Reject `3.12` and above with a clear stop message.
Recommend Python 3.11.

---

### Fix 3 — subtitle_generator.py: capture detected language from Whisper

**Applies to:** Phase 4 → Faster-Whisper integration

After transcription, capture `detected_language` from the Faster-Whisper
transcription info object and pass it to both:
- the logger (logs/success.log)
- the processed registry entry in processed_files.json

```python
segments, info = model.transcribe(audio_path, task="translate", ...)
detected_language = info.language  # capture this
```

Store `detected_language` in the processed registry and log it on success.

---

### Fix 4 — download_models.bat: use huggingface_hub Python API

**Applies to:** Phase 2 → `download_models.bat`

Use `huggingface_hub.snapshot_download()` via a small inline Python script
called from the BAT — **not** the `huggingface-cli` tool, which may not be
installed or available in the venv.

```bat
"%VENV_PYTHON%" -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Systran/faster-whisper-small', local_dir='%ROOT%models\small', local_dir_use_symlinks=False)"
```

Check exit code after each download call. If non-zero, print the model
download failure message and continue to the next model.

---

### Fix 5 — FFmpeg timeout: null means unlimited, do not use a fixed number

**Applies to:** Phase 1 → `config.json` default
**Applies to:** Phase 3 → FFmpeg audio extraction in `subtitle_generator.py`

**Reason:** Slow connections and large files (long movies, .ts files) need
unlimited processing time. A fixed timeout will incorrectly kill legitimate jobs.

Set `config.json` default to:

```json
"ffmpeg_timeout_seconds": null
```

In Python, pass the value directly to `subprocess.run` — it accepts `None`
as timeout which means wait forever:

```python
subprocess.run(
    ffmpeg_cmd,
    timeout=config["ffmpeg_timeout_seconds"]  # None = unlimited, no change needed
)
```

**Do NOT default to 1800 or any other fixed number.**

Config validation rule:
- `ffmpeg_timeout_seconds` must be a **positive integer or null**
- `null` means unlimited — this is valid and expected
- if the user sets it to `0` or a negative number, show a validation error

---

## Phase Completion Tracker

Update this table after each phase is complete and tested.

| Phase | Description                        | Status      | Notes |
|-------|------------------------------------|-------------|-------|
| 0     | Master spec pasted                 | [ ] pending |       |
| 1     | Project foundation                 | [x] complete | Phase 1 foundation files created and checked. |
| 2a    | install_cpu.bat                    | [ ] pending |       |
| 2b    | install_gpu.bat                    | [ ] pending |       |
| 2c    | download_models.bat                | [ ] pending |       |
| 2d    | download_ffmpeg.bat                | [ ] pending |       |
| 3     | Media scanner + FFmpeg pipeline    | [ ] pending |       |
| 4     | Faster-Whisper integration         | [ ] pending |       |
| 5     | SRT formatter + subtitle quality   | [ ] pending |       |
| 6     | Resume system + logging            | [ ] pending |       |
| 7     | run_subtitles.bat + drag-drop CLI  | [ ] pending |       |
| 8     | Final audit + README + testing     | [ ] pending |       |

---

## Per-Phase Mini Checklists

### Phase 1 — Project Foundation

- [x] `config.json` created with all defaults
- [x] `config.json` has `"ffmpeg_timeout_seconds": null` not 1800 (Fix 5)
- [x] `requirements.txt` created (no unnecessary packages)
- [x] `README.md` skeleton created
- [x] `subtitle_generator.py` skeleton created
- [x] All folders created on script run
- [x] `processed/processed_files.json` created if missing
- [x] `get_project_root()` implemented
- [x] `ensure_directories()` implemented
- [x] `set_local_environment()` implemented
- [x] `load_config()` implemented
- [x] `validate_config()` implemented with all field checks
- [x] `validate_config()` accepts null for ffmpeg_timeout_seconds (Fix 5)
- [x] `create_default_config()` implemented
- [x] `recover_corrupt_config()` implemented (rename + recreate)
- [x] `atomic_json_write()` implemented (tmp file + os.replace)
- [x] `load_processed_registry()` implemented
- [x] `recover_corrupt_processed_registry()` implemented
- [x] Script prints "Project foundation ready" without errors
- [x] No Whisper or FFmpeg code present

---

### Phase 2 — Setup Scripts

#### install_cpu.bat
- [ ] Uses `"%~dp0"` safely
- [ ] All paths quoted
- [ ] Python version detected via `python -c "..."` not `python --version` (Fix 2)
- [ ] Accepts 3.10 and 3.11 only
- [ ] Stops clearly on 3.12+
- [ ] Creates .venv if missing
- [ ] Activates .venv
- [ ] Sets all local cache/temp env vars
- [ ] Upgrades pip/setuptools/wheel
- [ ] Installs requirements.txt (CPU only, no CUDA packages)
- [ ] Verifies faster_whisper import
- [ ] Verifies ctranslate2 import + version
- [ ] Verifies tqdm import
- [ ] Verifies colorama import
- [ ] Stops with clear error if any verification fails
- [ ] Safe to rerun

#### install_gpu.bat
- [ ] Same as CPU checklist above
- [ ] Checks nvidia-smi
- [ ] Shows GPU name if available
- [ ] Shows CUDA version from nvidia-smi
- [ ] Maps CUDA version to correct PyTorch wheel index (cu124/cu121/cu118)
- [ ] Defaults to cu121 with warning if CUDA version undetected
- [ ] Stops if CUDA older than 11.8
- [ ] Verifies torch.cuda.is_available() after install
- [ ] Shows clear failure if CUDA unavailable after install
- [ ] Suggests install_cpu.bat if GPU fails

#### download_models.bat
- [ ] Activates .venv
- [ ] Sets local cache/model vars
- [ ] Uses `huggingface_hub.snapshot_download()` via inline Python (Fix 4)
- [ ] Does NOT use huggingface-cli (Fix 4)
- [ ] Downloads Systran/faster-whisper-small to models/small/
- [ ] Downloads Systran/faster-whisper-medium to models/medium/
- [ ] Skips already complete models
- [ ] Verifies model.bin, config.json, tokenizer.json, vocabulary.txt exist
- [ ] Handles 401/403 errors clearly
- [ ] Handles network failure clearly
- [ ] Safe to rerun

#### download_ffmpeg.bat
- [ ] Creates ffmpeg/ and ffmpeg/bin/
- [ ] Skips download if both .exe files already present and verified
- [ ] Tries primary source (gyan.dev) first
- [ ] Tries fallback source (BtbN) if primary fails
- [ ] Uses PowerShell Expand-Archive for extraction
- [ ] Searches recursively for ffmpeg.exe and ffprobe.exe (Fix 1)
- [ ] Does NOT hardcode internal ZIP folder path (Fix 1)
- [ ] Copies both to ffmpeg/bin/
- [ ] Verifies ffmpeg.exe -version
- [ ] Verifies ffprobe.exe -version
- [ ] Prints manual instructions if both downloads fail
- [ ] Safe to rerun

---

### Phase 3 — Media Scanner + FFmpeg Pipeline

- [ ] All 9 extensions supported (.mp4 .mkv .avi .mov .ts .mp3 .wav .m4a .flac)
- [ ] Scans all 5 language folders
- [ ] Respects recursive_scan config
- [ ] Correct language code mapping (ja/ru/hi/en/None)
- [ ] Output path preserves nested folder structure
- [ ] Output parent dirs created before writing (mkdir parents=True)
- [ ] FFmpeg path verified before processing
- [ ] subprocess.run with list args (no shell=True)
- [ ] FFmpeg timeout read from config and passed directly to subprocess (Fix 5)
- [ ] timeout=None means wait forever — no kill, no skip (Fix 5)
- [ ] Timeout kill only triggered if config value is a positive integer
- [ ] Unique temp WAV names using hash of path+size+mtime
- [ ] WAV validated after extraction (exists, size>0, duration>0)
- [ ] Failed validation logs error and skips file
- [ ] --dry-run scans without running FFmpeg
- [ ] Placeholder .srt written for testing (non-dry-run)
- [ ] File X of Y progress shown
- [ ] FFmpeg errors logged to error.log
- [ ] Skipped files logged to skipped.log

---

### Phase 4 — Faster-Whisper Integration

- [ ] task="translate" always used
- [ ] CUDA availability checked in Python (not just BAT)
- [ ] GPU mode: medium model, float16, cuda
- [ ] CPU mode: small model, int8, cpu
- [ ] Model folder verified before loading (all 4 required files)
- [ ] Clear error shown if model files incomplete
- [ ] No model download at runtime
- [ ] Language passed from folder mapping
- [ ] auto_detect passes no language to Whisper
- [ ] beam_size read from config
- [ ] detected_language captured from info object (Fix 3)
- [ ] detected_language passed to logger and processed registry (Fix 3)
- [ ] GPU fallback: retry with int8_float16 on CUDA error
- [ ] GPU fallback: fall back to CPU small if still failing
- [ ] Batch continues after per-file failures
- [ ] Import failure shows clear "rerun installer" message

---

### Phase 5 — SRT Formatter

- [ ] Valid UTF-8 .srt output
- [ ] Correct SRT index numbers
- [ ] Correct HH:MM:SS,mmm --> HH:MM:SS,mmm timestamps
- [ ] max 42 chars per line enforced
- [ ] max 2 lines per subtitle enforced
- [ ] Empty segments skipped
- [ ] Zero-duration segments skipped
- [ ] end time > start time enforced
- [ ] Tiny overlaps clamped safely
- [ ] Excessive whitespace removed
- [ ] Duplicate blank cues avoided
- [ ] Existing .srt not overwritten unless overwrite_existing=true or --overwrite
- [ ] Skipped files logged to skipped.log
- [ ] write_srt_metadata_note defaults to false
- [ ] No NOTE block written to .srt by default

---

### Phase 6 — Resume System + Logging

- [ ] processed_files.json read safely
- [ ] Missing file created automatically
- [ ] Corrupt file renamed with timestamp and recreated
- [ ] Corruption recovery event logged
- [ ] Tracks: path, size, mtime, output, language, detected_language, device, model, completion time, duration
- [ ] Skip logic: unchanged files skipped
- [ ] Skip logic: changed file (size or mtime) reprocessed
- [ ] Skip logic: missing output causes reprocess
- [ ] Atomic write: tmp file + os.replace()
- [ ] RotatingFileHandler used for all 3 logs
- [ ] log_max_bytes and log_backup_count from config
- [ ] success.log includes all required fields including detected_language
- [ ] error.log includes traceback where useful
- [ ] skipped.log includes reason
- [ ] CUDA fallback events logged
- [ ] Config recovery events logged
- [ ] Total runtime logged at end

---

### Phase 7 — run_subtitles.bat + CLI

- [ ] Uses "%~dp0" safely
- [ ] All paths quoted
- [ ] .venv existence checked
- [ ] .venv Python existence checked
- [ ] All 4 package imports verified
- [ ] All 8 model files verified (4 per model)
- [ ] FFmpeg existence verified
- [ ] CUDA detection runs
- [ ] Correct device/model passed to Python
- [ ] No installs or downloads in this BAT
- [ ] Helpful error messages for all missing prereqs
- [ ] Pauses at end
- [ ] Case 1: no args — batch mode works
- [ ] Case 2: --dry-run — dry-run batch works
- [ ] Case 3: dragged file — single file processed
- [ ] Case 4: --dry-run "file" — dry-run single file works
- [ ] Case 5: "file" --dry-run — dry-run single file works
- [ ] argparse supports all CLI flags
- [ ] CLI overrides config.json for that run only

---

### Phase 8 — Final Audit

- [ ] All Phase 8 audit checklist items verified in code
- [ ] README.md complete with all sections
- [ ] Troubleshooting section covers all listed scenarios
- [ ] Manual FFmpeg setup explained in README
- [ ] Final test checklist added to README
- [ ] No runtime installs anywhere in subtitle_generator.py
- [ ] No runtime model downloads anywhere
- [ ] Fix 1 confirmed: recursive ZIP search in download_ffmpeg.bat
- [ ] Fix 2 confirmed: Python version via python -c in both installers
- [ ] Fix 3 confirmed: detected_language captured and stored
- [ ] Fix 4 confirmed: snapshot_download used in download_models.bat
- [ ] Fix 5 confirmed: ffmpeg_timeout_seconds is null, timeout=None passed to subprocess

---

## Final File List

All of these must exist when Phase 8 is complete:

```
ProjectRoot/
├── run_subtitles.bat
├── install_cpu.bat
├── install_gpu.bat
├── download_models.bat
├── download_ffmpeg.bat
├── subtitle_generator.py
├── config.json
├── requirements.txt
├── README.md
├── CHECKLIST.md
├── SPEC.md
├── ffmpeg/bin/          (populated by download_ffmpeg.bat)
├── models/small/        (populated by download_models.bat)
├── models/medium/       (populated by download_models.bat)
├── cache/
├── logs/
├── temp/
├── output_subtitles/
├── processed/
│   └── processed_files.json
└── videos/
    ├── japanese/
    ├── russian/
    ├── english/
    ├── hindi/
    └── auto_detect/
```

---

## How to Use This File

1. Keep `CHECKLIST.md` and `SPEC.md` in the project root
2. At the start of every phase prompt, prepend:
   > "Read CHECKLIST.md and SPEC.md first. Then do Phase X only."
3. After each phase, tick completed items and update the status table
4. If the AI misses something, say:
   > "Stop. Re-read CHECKLIST.md Fix [number] and correct your output."
5. Before Phase 8, scan for any unticked boxes and fix them first
