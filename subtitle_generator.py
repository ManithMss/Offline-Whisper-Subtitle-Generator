from __future__ import annotations

import json
import os
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


def main() -> int:
    project_root = get_project_root()
    ensure_directories(project_root)
    set_local_environment(project_root)
    load_config(project_root)
    load_processed_registry(project_root)
    print("Project foundation ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
