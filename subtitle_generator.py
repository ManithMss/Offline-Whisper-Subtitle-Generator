from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "overwrite_existing": False,
    "recursive_scan": True,
    "cleanup_temp": True,
    "beam_size": 5,
    "max_chars_per_line": 42,
    "max_lines_per_subtitle": 2,
    "audio_sample_rate": 16000,
    "audio_channels": 1,
    "translate_to_english": True,
    "log_success": True,
    "log_errors": True,
    "log_skipped": True,
    "ffmpeg_timeout_seconds": None,
    "log_max_bytes": 5_242_880,
    "log_backup_count": 3,
    "write_srt_metadata_note": False,
}

REQUIRED_DIRECTORIES = (
    "ffmpeg/bin",
    "models/small",
    "models/medium",
    "cache",
    "cache/huggingface",
    "cache/transformers",
    "cache/torch",
    "cache/pip",
    "logs",
    "temp",
    "output_subtitles",
    "processed",
    "videos/japanese",
    "videos/russian",
    "videos/english",
    "videos/hindi",
    "videos/auto_detect",
)

LOCAL_ENVIRONMENT_PATHS = {
    "HF_HOME": "cache/huggingface",
    "HUGGINGFACE_HUB_CACHE": "cache/huggingface/hub",
    "TRANSFORMERS_CACHE": "cache/transformers",
    "TORCH_HOME": "cache/torch",
    "XDG_CACHE_HOME": "cache",
    "TEMP": "temp",
    "TMP": "temp",
    "PIP_CACHE_DIR": "cache/pip",
}

SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".ts",
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
}

LANGUAGE_FOLDERS: dict[str, str | None] = {
    "japanese": "ja",
    "russian": "ru",
    "hindi": "hi",
    "english": "en",
    "auto_detect": None,
}


class ConfigValidationError(ValueError):
    """Raised when config.json contains values the project cannot use safely."""


def get_project_root() -> Path:
    return Path(__file__).resolve().parent


def ensure_directories(project_root: Path) -> None:
    for relative_path in REQUIRED_DIRECTORIES:
        (project_root / relative_path).mkdir(parents=True, exist_ok=True)


def set_local_environment(project_root: Path) -> None:
    for name, relative_path in LOCAL_ENVIRONMENT_PATHS.items():
        path = project_root / relative_path
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)


def timestamp_for_filename() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def atomic_json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2)
        file_handle.write("\n")
        file_handle.flush()
        os.fsync(file_handle.fileno())
    os.replace(temp_path, path)


def create_default_config(project_root: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    atomic_json_write(project_root / "config.json", config)
    return config


def require_bool(config: dict[str, Any], key: str) -> None:
    if not isinstance(config.get(key), bool):
        raise ConfigValidationError(f"{key} must be true or false.")


def require_int_min(config: dict[str, Any], key: str, minimum: int) -> None:
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigValidationError(f"{key} must be an integer >= {minimum}.")


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(DEFAULT_CONFIG)
    normalized.update(config)

    for key in (
        "overwrite_existing",
        "recursive_scan",
        "cleanup_temp",
        "translate_to_english",
        "log_success",
        "log_errors",
        "log_skipped",
        "write_srt_metadata_note",
    ):
        require_bool(normalized, key)

    require_int_min(normalized, "beam_size", 1)
    require_int_min(normalized, "max_chars_per_line", 10)
    require_int_min(normalized, "max_lines_per_subtitle", 1)
    require_int_min(normalized, "audio_sample_rate", 1)
    require_int_min(normalized, "audio_channels", 1)
    require_int_min(normalized, "log_max_bytes", 1)
    require_int_min(normalized, "log_backup_count", 0)

    timeout = normalized.get("ffmpeg_timeout_seconds")
    if timeout is not None:
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ConfigValidationError(
                "ffmpeg_timeout_seconds must be a positive integer or null."
            )

    return normalized


def recover_corrupt_config(project_root: Path, config_path: Path) -> dict[str, Any]:
    recovered_path = project_root / f"config.corrupt.{timestamp_for_filename()}.json"
    config_path.replace(recovered_path)
    print(f"Corrupt config.json renamed to {recovered_path.name}.")
    return create_default_config(project_root)


def load_config(project_root: Path) -> dict[str, Any]:
    config_path = project_root / "config.json"
    if not config_path.exists():
        return create_default_config(project_root)

    try:
        with config_path.open("r", encoding="utf-8") as file_handle:
            loaded_config = json.load(file_handle)
    except json.JSONDecodeError:
        return recover_corrupt_config(project_root, config_path)

    if not isinstance(loaded_config, dict):
        raise ConfigValidationError("config.json must contain a JSON object.")

    try:
        config = validate_config(loaded_config)
    except ConfigValidationError as error:
        raise ConfigValidationError(f"Invalid config.json: {error}") from error

    if config != loaded_config:
        atomic_json_write(config_path, config)

    return config


def default_processed_registry() -> dict[str, Any]:
    return {
        "version": 1,
        "files": {},
    }


def recover_corrupt_processed_registry(
    project_root: Path, registry_path: Path
) -> dict[str, Any]:
    recovered_path = (
        project_root
        / "processed"
        / f"processed_files.corrupt.{timestamp_for_filename()}.json"
    )
    registry_path.replace(recovered_path)
    print(f"Corrupt processed registry renamed to {recovered_path.name}.")
    registry = default_processed_registry()
    atomic_json_write(registry_path, registry)
    return registry


def load_processed_registry(project_root: Path) -> dict[str, Any]:
    registry_path = project_root / "processed" / "processed_files.json"
    if not registry_path.exists():
        registry = default_processed_registry()
        atomic_json_write(registry_path, registry)
        return registry

    try:
        with registry_path.open("r", encoding="utf-8") as file_handle:
            registry = json.load(file_handle)
    except json.JSONDecodeError:
        return recover_corrupt_processed_registry(project_root, registry_path)

    if not isinstance(registry, dict) or not isinstance(registry.get("files"), dict):
        return recover_corrupt_processed_registry(project_root, registry_path)

    return registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate local English subtitle files from media."
    )
    parser.add_argument("--dry-run", action="store_true", help="Scan without processing.")
    parser.add_argument("--input", type=Path, help="Process one media file.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing subtitles for this run.",
    )
    return parser.parse_args()


def log_line(project_root: Path, log_name: str, message: str) -> None:
    log_path = project_root / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} {message}\n")


def log_error(project_root: Path, input_path: Path, message: str) -> None:
    log_line(project_root, "error.log", f'input="{input_path}" error="{message}"')


def log_skipped(project_root: Path, input_path: Path, reason: str) -> None:
    log_line(project_root, "skipped.log", f'input="{input_path}" reason="{reason}"')


def language_for_folder(folder_name: str) -> str | None:
    return LANGUAGE_FOLDERS[folder_name]


def iter_media_files(folder: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    return sorted(
        path
        for path in folder.glob(pattern)
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def describe_media_file(
    project_root: Path, input_path: Path, language_folder: str, base_folder: Path
) -> dict[str, Any]:
    relative_path = input_path.relative_to(base_folder)
    output_path = (
        project_root / "output_subtitles" / language_folder / relative_path
    ).with_suffix(".en.srt")
    return {
        "input_path": input_path,
        "language_folder": language_folder,
        "language": language_for_folder(language_folder),
        "output_path": output_path,
    }


def describe_single_input(project_root: Path, input_path: Path) -> dict[str, Any]:
    resolved_input = input_path.resolve()
    videos_root = project_root / "videos"
    for language_folder in LANGUAGE_FOLDERS:
        folder = videos_root / language_folder
        try:
            resolved_input.relative_to(folder)
        except ValueError:
            continue
        return describe_media_file(project_root, resolved_input, language_folder, folder)

    return {
        "input_path": resolved_input,
        "language_folder": "auto_detect",
        "language": None,
        "output_path": project_root
        / "output_subtitles"
        / "auto_detect"
        / f"{resolved_input.stem}.en.srt",
    }


def scan_media(project_root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    media_files: list[dict[str, Any]] = []
    videos_root = project_root / "videos"
    for language_folder in LANGUAGE_FOLDERS:
        folder = videos_root / language_folder
        for input_path in iter_media_files(folder, config["recursive_scan"]):
            media_files.append(
                describe_media_file(project_root, input_path, language_folder, folder)
            )
    return media_files


def scan_requested_media(
    project_root: Path, config: dict[str, Any], input_path: Path | None
) -> list[dict[str, Any]]:
    if input_path is None:
        return scan_media(project_root, config)

    resolved_input = input_path.resolve()
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file not found: {resolved_input}")
    if not resolved_input.is_file():
        raise ValueError(f"Input path is not a file: {resolved_input}")
    if resolved_input.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input extension: {resolved_input.suffix}")
    return [describe_single_input(project_root, resolved_input)]


def verify_ffmpeg(project_root: Path) -> tuple[Path, Path]:
    ffmpeg_path = project_root / "ffmpeg" / "bin" / "ffmpeg.exe"
    ffprobe_path = project_root / "ffmpeg" / "bin" / "ffprobe.exe"
    if not ffmpeg_path.exists() or not ffprobe_path.exists():
        raise FileNotFoundError(
            "FFmpeg not found. Please run download_ffmpeg.bat first."
        )
    return ffmpeg_path, ffprobe_path


def unique_temp_audio_path(project_root: Path, input_path: Path) -> Path:
    stat = input_path.stat()
    identity = (
        f"{input_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}|{os.getpid()}"
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return project_root / "temp" / f"audio_{digest}.wav"


def extract_audio_to_wav(
    project_root: Path,
    config: dict[str, Any],
    input_path: Path,
    temp_wav_path: Path,
    ffmpeg_path: Path,
) -> bool:
    temp_wav_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg_path),
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(config["audio_sample_rate"]),
        "-ac",
        str(config["audio_channels"]),
        str(temp_wav_path),
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=config["ffmpeg_timeout_seconds"],
        )
    except subprocess.TimeoutExpired:
        log_error(project_root, input_path, "FFmpeg timeout expired.")
        return False

    if result.returncode != 0:
        message = result.stderr.strip() or f"FFmpeg exited with {result.returncode}."
        log_error(project_root, input_path, message)
        return False

    return True


def probe_wav_duration(
    project_root: Path, wav_path: Path, ffprobe_path: Path, source_path: Path
) -> float | None:
    command = [
        str(ffprobe_path),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(wav_path),
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "ffprobe could not read WAV duration."
        log_error(project_root, source_path, message)
        return None

    try:
        return float(result.stdout.strip())
    except ValueError:
        log_error(project_root, source_path, "ffprobe returned invalid WAV duration.")
        return None


def validate_wav(
    project_root: Path, wav_path: Path, ffprobe_path: Path, source_path: Path
) -> bool:
    if not wav_path.exists():
        log_error(project_root, source_path, "Extracted WAV does not exist.")
        return False
    if wav_path.stat().st_size <= 0:
        log_error(project_root, source_path, "Extracted WAV is empty.")
        return False

    duration = probe_wav_duration(project_root, wav_path, ffprobe_path, source_path)
    if duration is None or duration <= 0:
        log_error(project_root, source_path, "Extracted WAV duration is not positive.")
        return False
    return True


def write_placeholder_srt(output_path: Path, input_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "1\n"
        "00:00:00,000 --> 00:00:02,000\n"
        "[Placeholder subtitle - Whisper integration pending]\n"
        f"# Source: {input_path}\n"
    )
    output_path.write_text(content, encoding="utf-8")


def should_skip_existing_output(
    project_root: Path,
    media: dict[str, Any],
    config: dict[str, Any],
    overwrite: bool,
) -> bool:
    output_path = media["output_path"]
    if output_path.exists() and not config["overwrite_existing"] and not overwrite:
        log_skipped(project_root, media["input_path"], "subtitle already exists")
        return True
    return False


def print_dry_run(media_files: list[dict[str, Any]], project_root: Path) -> None:
    print(f"Dry run: {len(media_files)} media file(s) found.")
    for index, media in enumerate(media_files, start=1):
        status = "SKIP existing" if media["output_path"].exists() else "WOULD process"
        print(f"File {index} of {len(media_files)}")
        print(f"Current file: {media['input_path']}")
        print(f"Language: {media['language_folder']} ({media['language']})")
        print(f"Output path: {media['output_path']}")
        print(status)
        if status.startswith("SKIP"):
            log_skipped(project_root, media["input_path"], "subtitle already exists")


def process_media_files(
    project_root: Path,
    config: dict[str, Any],
    media_files: list[dict[str, Any]],
    overwrite: bool,
) -> tuple[int, int, int]:
    processed = 0
    skipped = 0
    failed = 0

    if not media_files:
        return processed, skipped, failed

    try:
        ffmpeg_path, ffprobe_path = verify_ffmpeg(project_root)
    except FileNotFoundError as error:
        print(str(error))
        for media in media_files:
            log_error(project_root, media["input_path"], str(error))
        return 0, 0, len(media_files)

    for index, media in enumerate(media_files, start=1):
        input_path = media["input_path"]
        output_path = media["output_path"]
        print(f"File {index} of {len(media_files)}")
        print(f"Current file: {input_path}")
        print(f"Output path: {output_path}")

        if should_skip_existing_output(project_root, media, config, overwrite):
            skipped += 1
            print("Skipped: subtitle already exists.")
            continue

        temp_wav_path = unique_temp_audio_path(project_root, input_path)
        extracted = extract_audio_to_wav(
            project_root, config, input_path, temp_wav_path, ffmpeg_path
        )
        if not extracted:
            failed += 1
            print("Failed: FFmpeg extraction failed.")
            continue

        if not validate_wav(project_root, temp_wav_path, ffprobe_path, input_path):
            failed += 1
            print("Failed: extracted WAV validation failed.")
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_placeholder_srt(output_path, input_path)
        processed += 1
        print("Processed: placeholder subtitle written.")

        if config["cleanup_temp"] and temp_wav_path.exists():
            temp_wav_path.unlink()

    return processed, skipped, failed


def main() -> int:
    args = parse_args()
    project_root = get_project_root()
    ensure_directories(project_root)
    set_local_environment(project_root)
    config = load_config(project_root)
    load_processed_registry(project_root)

    try:
        media_files = scan_requested_media(project_root, config, args.input)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    if args.dry_run:
        print_dry_run(media_files, project_root)
        return 0

    processed, skipped, failed = process_media_files(
        project_root, config, media_files, args.overwrite
    )
    print()
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Output Folder: {project_root / 'output_subtitles'}")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
