from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
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

REQUIRED_MODEL_FILES = (
    "model.bin",
    "config.json",
    "tokenizer.json",
    "vocabulary.txt",
)

LOGGERS: dict[str, logging.Logger] = {}
PENDING_RECOVERY_EVENTS: list[tuple[str, str]] = []


class ConfigValidationError(ValueError):
    """Raised when config.json contains values the project cannot use safely."""


class DependencyError(RuntimeError):
    """Raised when installed Python dependencies are missing or incomplete."""


class ModelFilesError(RuntimeError):
    """Raised when local Faster-Whisper model files are missing or incomplete."""


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
    message = f"Corrupt config.json renamed to {recovered_path.name}."
    print(message)
    PENDING_RECOVERY_EVENTS.append(("error.log", message))
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
    message = f"Corrupt processed registry renamed to {recovered_path.name}."
    print(message)
    registry = default_processed_registry()
    atomic_json_write(registry_path, registry)
    log_line(project_root, "error.log", message)
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
    parser.add_argument("positional_input", nargs="?", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing subtitles for this run.",
    )
    parser.add_argument("--device", choices=("cpu", "cuda"), help="Override device.")
    parser.add_argument("--model", choices=("small", "medium"), help="Override model.")
    args = parser.parse_args()
    if args.input is not None and args.positional_input is not None:
        parser.error("Use either --input or a positional input path, not both.")
    if args.input is None:
        args.input = args.positional_input
    return args


def setup_logging(project_root: Path, config: dict[str, Any]) -> None:
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for log_name in ("success.log", "error.log", "skipped.log"):
        logger = logging.getLogger(f"subtitle_generator.{log_name}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        handler = RotatingFileHandler(
            log_dir / log_name,
            maxBytes=config["log_max_bytes"],
            backupCount=config["log_backup_count"],
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        LOGGERS[log_name] = logger


def flush_pending_recovery_events(project_root: Path) -> None:
    while PENDING_RECOVERY_EVENTS:
        log_name, message = PENDING_RECOVERY_EVENTS.pop(0)
        log_line(project_root, log_name, message)


def log_line(
    project_root: Path,
    log_name: str,
    message: str,
    level: int = logging.INFO,
    exc_info: bool = False,
) -> None:
    logger = LOGGERS.get(log_name)
    if logger is not None:
        logger.log(level, message, exc_info=exc_info)
        return

    log_path = project_root / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} {message}\n")


def log_error(
    project_root: Path, input_path: Path, message: str, exc_info: bool = False
) -> None:
    log_line(
        project_root,
        "error.log",
        f'input="{input_path}" error="{message}"',
        level=logging.ERROR,
        exc_info=exc_info,
    )


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


def format_srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def sanitize_subtitle_text(text: str) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def split_long_word(word: str, max_chars: int) -> list[str]:
    if len(word) <= max_chars:
        return [word]
    return [word[index : index + max_chars] for index in range(0, len(word), max_chars)]


def wrap_subtitle_text(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    current_line = ""
    for word in text.split():
        pieces = split_long_word(word, max_chars)
        for piece in pieces:
            if not current_line:
                current_line = piece
            elif len(current_line) + 1 + len(piece) <= max_chars:
                current_line = f"{current_line} {piece}"
            else:
                lines.append(current_line)
                current_line = piece
    if current_line:
        lines.append(current_line)
    return lines


def chunk_subtitle_lines(lines: list[str], max_lines: int) -> list[list[str]]:
    return [
        lines[index : index + max_lines]
        for index in range(0, len(lines), max_lines)
        if lines[index : index + max_lines]
    ]


def segment_times(segment: Any) -> tuple[float, float] | None:
    try:
        start = float(getattr(segment, "start", 0.0))
        end = float(getattr(segment, "end", start))
    except (TypeError, ValueError):
        return None

    if end <= start:
        return None
    return max(0.0, start), max(0.0, end)


def build_srt_cues(segments: list[Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    previous_end = 0.0
    max_chars = config["max_chars_per_line"]
    max_lines = config["max_lines_per_subtitle"]

    for segment in segments:
        text = sanitize_subtitle_text(str(getattr(segment, "text", "")))
        if not text:
            continue

        times = segment_times(segment)
        if times is None:
            continue
        segment_start, segment_end = times

        wrapped_lines = wrap_subtitle_text(text, max_chars)
        line_chunks = chunk_subtitle_lines(wrapped_lines, max_lines)
        if not line_chunks:
            continue

        segment_duration = segment_end - segment_start
        chunk_duration = segment_duration / len(line_chunks)
        for chunk_index, lines in enumerate(line_chunks):
            start = segment_start + (chunk_index * chunk_duration)
            end = (
                segment_end
                if chunk_index == len(line_chunks) - 1
                else segment_start + ((chunk_index + 1) * chunk_duration)
            )
            if start < previous_end:
                start = previous_end
            if end <= start:
                continue
            cues.append({"start": start, "end": end, "lines": lines})
            previous_end = end

    return cues


def write_transcribed_srt(
    output_path: Path, segments: list[Any], config: dict[str, Any]
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cue_lines: list[str] = []
    for index, cue in enumerate(build_srt_cues(segments, config), start=1):
        cue_lines.extend(
            [
                str(index),
                (
                    f"{format_srt_timestamp(cue['start'])} --> "
                    f"{format_srt_timestamp(cue['end'])}"
                ),
                *cue["lines"],
                "",
            ]
        )
    output_path.write_text("\n".join(cue_lines).rstrip() + "\n", encoding="utf-8")


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


def registry_entry_matches_file(entry: dict[str, Any], input_path: Path) -> bool:
    stat = input_path.stat()
    entry_size = entry.get("size", entry.get("file_size"))
    entry_mtime = entry.get("mtime", entry.get("modified_time"))
    return entry_size == stat.st_size and entry_mtime == stat.st_mtime


def should_skip_processed_file(
    project_root: Path,
    registry: dict[str, Any],
    media: dict[str, Any],
    overwrite: bool,
) -> bool:
    if overwrite:
        return False

    input_path = media["input_path"]
    output_path = media["output_path"]
    entry = registry.get("files", {}).get(str(input_path))
    if not isinstance(entry, dict):
        return False
    if not output_path.exists():
        return False
    if not registry_entry_matches_file(entry, input_path):
        return False

    log_skipped(project_root, input_path, "already processed and unchanged")
    return True


def import_whisper_dependencies() -> tuple[Any, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise DependencyError(
            "Virtual environment exists but dependencies are incomplete. "
            "Please rerun install_cpu.bat or install_gpu.bat."
        ) from error

    try:
        import ctranslate2
    except ImportError as error:
        raise DependencyError(
            "Virtual environment exists but dependencies are incomplete. "
            "Please rerun install_cpu.bat or install_gpu.bat."
        ) from error

    return WhisperModel, ctranslate2


def cuda_available_in_python(ctranslate2_module: Any) -> bool:
    try:
        get_count = getattr(ctranslate2_module, "get_cuda_device_count")
        return int(get_count()) > 0
    except Exception:
        pass

    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def choose_processing_plan(
    project_root: Path, ctranslate2_module: Any, args: argparse.Namespace
) -> dict[str, str]:
    cuda_available = cuda_available_in_python(ctranslate2_module)
    if args.device:
        device = args.device
        if device == "cuda" and cuda_available:
            print("CUDA GPU detected. Using GPU acceleration.")
        elif device == "cuda":
            print("No CUDA GPU detected. Using CPU processing.")
            device = "cpu"
        else:
            print("No CUDA GPU detected. Using CPU processing.")
    elif cuda_available:
        print("CUDA GPU detected. Using GPU acceleration.")
        device = "cuda"
    else:
        print("No CUDA GPU detected. Using CPU processing.")
        device = "cpu"

    model_name = args.model or ("medium" if device == "cuda" else "small")
    compute_type = "float16" if device == "cuda" else "int8"
    if device == "cpu" and model_name != "small" and not args.model:
        model_name = "small"
    if device == "cuda" and model_name != "medium" and not args.model:
        model_name = "medium"

    return {
        "device": device,
        "model_name": model_name,
        "model_dir": str(project_root / "models" / model_name),
        "compute_type": compute_type,
    }


def verify_model_files(project_root: Path, model_name: str) -> Path:
    model_dir = project_root / "models" / model_name
    missing = [name for name in REQUIRED_MODEL_FILES if not (model_dir / name).exists()]
    if missing:
        raise ModelFilesError(
            "Model files are incomplete. Please rerun download_models.bat."
        )
    return model_dir


def load_whisper_model(
    WhisperModel: Any,
    project_root: Path,
    model_name: str,
    device: str,
    compute_type: str,
) -> Any:
    model_dir = verify_model_files(project_root, model_name)
    return WhisperModel(str(model_dir), device=device, compute_type=compute_type)


def is_cuda_failure(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "cuda",
            "vram",
            "out of memory",
            "out-of-memory",
            "ctranslate2",
            "cublas",
            "cudnn",
        )
    )


def transcribe_with_whisper(
    WhisperModel: Any,
    project_root: Path,
    config: dict[str, Any],
    audio_path: Path,
    language: str | None,
    plan: dict[str, str],
) -> dict[str, Any]:
    attempts: list[dict[str, str]] = [dict(plan)]
    if plan["device"] == "cuda":
        attempts.append(
            {
                "device": "cuda",
                "model_name": "medium",
                "model_dir": str(project_root / "models" / "medium"),
                "compute_type": "int8_float16",
            }
        )
        attempts.append(
            {
                "device": "cpu",
                "model_name": "small",
                "model_dir": str(project_root / "models" / "small"),
                "compute_type": "int8",
            }
        )

    last_error: Exception | None = None
    for attempt_index, attempt in enumerate(attempts, start=1):
        try:
            model = load_whisper_model(
                WhisperModel,
                project_root,
                attempt["model_name"],
                attempt["device"],
                attempt["compute_type"],
            )
            transcribe_args: dict[str, Any] = {
                "task": "translate",
                "beam_size": config["beam_size"],
            }
            if language is not None:
                transcribe_args["language"] = language
            segments, info = model.transcribe(str(audio_path), **transcribe_args)
            segment_list = list(segments)
            detected_language = info.language
            return {
                "segments": segment_list,
                "detected_language": detected_language,
                "device": attempt["device"],
                "model_name": attempt["model_name"],
                "compute_type": attempt["compute_type"],
            }
        except ModelFilesError:
            raise
        except Exception as error:
            last_error = error
            if plan["device"] == "cuda" and is_cuda_failure(error):
                if attempt_index == 1:
                    log_line(
                        project_root,
                        "error.log",
                        "CUDA processing failed. Retrying GPU with int8_float16.",
                    )
                    continue
                if attempt_index == 2:
                    log_line(
                        project_root,
                        "error.log",
                        "CUDA retry failed. Falling back to CPU small model.",
                    )
                    continue
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("Faster-Whisper transcription did not produce a result.")


def log_success(
    project_root: Path,
    input_path: Path,
    output_path: Path,
    language: str | None,
    detected_language: str | None,
    device: str,
    model_name: str,
    duration: float | None,
) -> None:
    log_line(
        project_root,
        "success.log",
        (
            f'input="{input_path}" output="{output_path}" language="{language}" '
            f'detected_language="{detected_language}" device="{device}" '
            f'model="{model_name}" duration="{duration}"'
        ),
    )


def update_processed_registry(
    project_root: Path,
    registry: dict[str, Any],
    input_path: Path,
    output_path: Path,
    language: str | None,
    detected_language: str | None,
    device: str,
    model_name: str,
    duration: float | None,
) -> None:
    stat = input_path.stat()
    registry.setdefault("files", {})[str(input_path)] = {
        "input_path": str(input_path),
        "path": str(input_path),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "file_size": stat.st_size,
        "modified_time": stat.st_mtime,
        "output_path": str(output_path),
        "output": str(output_path),
        "language": language,
        "detected_language": detected_language,
        "device": device,
        "model": model_name,
        "completion_time": datetime.now().isoformat(timespec="seconds"),
        "duration": duration,
    }
    atomic_json_write(project_root / "processed" / "processed_files.json", registry)


def format_runtime(seconds: float) -> str:
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def log_runtime_summary(
    project_root: Path, processed: int, skipped: int, failed: int, started_at: float
) -> None:
    runtime = format_runtime(time.monotonic() - started_at)
    log_line(
        project_root,
        "success.log",
        (
            f'total_runtime="{runtime}" processed="{processed}" '
            f'skipped="{skipped}" failed="{failed}"'
        ),
    )


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
    registry: dict[str, Any],
    media_files: list[dict[str, Any]],
    overwrite: bool,
    args: argparse.Namespace,
) -> tuple[int, int, int, str | None, str | None]:
    processed = 0
    skipped = 0
    failed = 0
    summary_device: str | None = None
    summary_model: str | None = None

    if not media_files:
        return processed, skipped, failed, summary_device, summary_model

    try:
        WhisperModel, ctranslate2_module = import_whisper_dependencies()
        plan = choose_processing_plan(project_root, ctranslate2_module, args)
        summary_device = plan["device"]
        summary_model = plan["model_name"]
        verify_model_files(project_root, plan["model_name"])
    except (DependencyError, ModelFilesError) as error:
        print(str(error))
        for media in media_files:
            log_error(project_root, media["input_path"], str(error))
        return 0, 0, len(media_files), summary_device, summary_model

    try:
        ffmpeg_path, ffprobe_path = verify_ffmpeg(project_root)
    except FileNotFoundError as error:
        print(str(error))
        for media in media_files:
            log_error(project_root, media["input_path"], str(error))
        return 0, 0, len(media_files), summary_device, summary_model

    for index, media in enumerate(media_files, start=1):
        input_path = media["input_path"]
        output_path = media["output_path"]
        print(f"File {index} of {len(media_files)}")
        print(f"Current file: {input_path}")
        print(f"Output path: {output_path}")
        print(f"Selected device: {plan['device']}")
        print(f"Selected model: {plan['model_name']}")

        if should_skip_processed_file(project_root, registry, media, overwrite):
            skipped += 1
            print("Skipped: already processed and unchanged.")
            continue

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

        duration = probe_wav_duration(project_root, temp_wav_path, ffprobe_path, input_path)

        try:
            transcription = transcribe_with_whisper(
                WhisperModel,
                project_root,
                config,
                temp_wav_path,
                media["language"],
                plan,
            )
            write_transcribed_srt(output_path, transcription["segments"], config)
            summary_device = transcription["device"]
            summary_model = transcription["model_name"]
            log_success(
                project_root,
                input_path,
                output_path,
                media["language"],
                transcription["detected_language"],
                transcription["device"],
                transcription["model_name"],
                duration,
            )
            update_processed_registry(
                project_root,
                registry,
                input_path,
                output_path,
                media["language"],
                transcription["detected_language"],
                transcription["device"],
                transcription["model_name"],
                duration,
            )
        except ModelFilesError as error:
            failed += 1
            log_error(project_root, input_path, str(error))
            print(f"Failed: {error}")
            continue
        except Exception as error:
            failed += 1
            log_error(
                project_root,
                input_path,
                f"Faster-Whisper failed: {error}",
                exc_info=True,
            )
            print("Failed: Faster-Whisper processing failed.")
            continue

        processed += 1
        print("Processed: subtitle written.")

        if config["cleanup_temp"] and temp_wav_path.exists():
            temp_wav_path.unlink()

    return processed, skipped, failed, summary_device, summary_model


def main() -> int:
    started_at = time.monotonic()
    args = parse_args()
    project_root = get_project_root()
    ensure_directories(project_root)
    set_local_environment(project_root)
    config = load_config(project_root)
    setup_logging(project_root, config)
    flush_pending_recovery_events(project_root)
    registry = load_processed_registry(project_root)

    try:
        media_files = scan_requested_media(project_root, config, args.input)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}")
        log_line(project_root, "error.log", f"startup_error={error}", level=logging.ERROR)
        log_runtime_summary(project_root, 0, 0, 1, started_at)
        return 1

    if args.dry_run:
        print_dry_run(media_files, project_root)
        log_runtime_summary(project_root, 0, 0, 0, started_at)
        return 0

    processed, skipped, failed, device_used, model_used = process_media_files(
        project_root, config, registry, media_files, args.overwrite, args
    )
    runtime = format_runtime(time.monotonic() - started_at)
    print()
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Total Runtime: {runtime}")
    print(f"Output Folder: {project_root / 'output_subtitles'}")
    if device_used:
        device_label = "GPU" if device_used == "cuda" else "CPU"
        print(f"Device Used: {device_label}")
    else:
        print("Device Used: unavailable")
    if model_used:
        print(f"Model Used: {model_used}")
    else:
        print("Model Used: unavailable")
    log_runtime_summary(project_root, processed, skipped, failed, started_at)
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
