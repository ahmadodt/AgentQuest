import json
import os
from typing import Any

from src.runner.benchmark_report import load_benchmark_bundle
from src.runner.benchmark_service import collect_dataset_metadata
from src.runner.runner_utils import get_results_dir, write_json_file


BENCHMARK_FILENAMES = ("manifest.json", "summary.json", "records.json")
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_SHOWCASE_DIR = os.path.join(_PROJECT_ROOT, "showcase", "benchmarks")


def discover_benchmark_bundles(
    *,
    data_dir: str,
    showcase_dir: str = DEFAULT_SHOWCASE_DIR,
    local_dir: str = "",
) -> list[dict[str, Any]]:
    current_dataset = collect_dataset_metadata(data_dir)
    roots = [
        ("curated", os.path.abspath(showcase_dir)),
        ("local", os.path.abspath(local_dir or os.path.join(get_results_dir(), "benchmarks"))),
    ]
    discovered: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for source, root in roots:
        for benchmark_dir in _discover_bundle_dirs(root):
            try:
                bundle = load_benchmark_bundle(benchmark_dir)
                _validate_bundle(bundle)
            except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
                continue
            identity = _bundle_identity(bundle)
            if identity in seen:
                continue
            seen.add(identity)
            bundle["source"] = source
            bundle["showcase"] = _read_optional_json(os.path.join(benchmark_dir, "showcase.json"))
            bundle["compatibility"] = compare_dataset_metadata(bundle["manifest"], current_dataset)
            discovered.append(bundle)

    return sorted(
        discovered,
        key=lambda item: str(item["manifest"].get("timestamp") or ""),
        reverse=True,
    )


def compare_dataset_metadata(
    manifest: dict[str, Any],
    current_dataset: dict[str, Any],
) -> dict[str, Any]:
    saved_dataset = manifest.get("dataset") or {}
    saved_fingerprint = str(saved_dataset.get("dataset_fingerprint") or "")
    current_fingerprint = str(current_dataset.get("dataset_fingerprint") or "")
    if not saved_fingerprint:
        return {
            "status": "unknown",
            "label": "Unknown dataset",
            "matches": False,
            "differences": [],
        }
    if saved_fingerprint == current_fingerprint:
        return {
            "status": "exact",
            "label": "Exact dataset match",
            "matches": True,
            "differences": [],
        }

    differences = []
    saved_files = saved_dataset.get("files") or {}
    current_files = current_dataset.get("files") or {}
    for key in sorted(set(saved_files) | set(current_files)):
        saved_version = str((saved_files.get(key) or {}).get("version") or "missing")
        current_version = str((current_files.get(key) or {}).get("version") or "missing")
        saved_hash = str((saved_files.get(key) or {}).get("sha256") or "")
        current_hash = str((current_files.get(key) or {}).get("sha256") or "")
        if saved_hash != current_hash:
            differences.append(f"{key}: {saved_version} -> {current_version}")
    return {
        "status": "mismatch",
        "label": "Dataset mismatch",
        "matches": False,
        "differences": differences,
    }


def publish_benchmark_showcase(
    benchmark_dir: str,
    *,
    showcase_id: str,
    title: str = "",
    description: str = "",
    showcase_dir: str = DEFAULT_SHOWCASE_DIR,
) -> str:
    source_dir = os.path.abspath(benchmark_dir)
    bundle = load_benchmark_bundle(source_dir)
    _validate_bundle(bundle)
    safe_id = _safe_showcase_id(showcase_id)
    destination = os.path.abspath(os.path.join(showcase_dir, safe_id))
    if os.path.commonpath([destination, os.path.abspath(showcase_dir)]) != os.path.abspath(showcase_dir):
        raise ValueError("Showcase destination must stay inside the showcase directory.")
    if os.path.exists(destination):
        raise FileExistsError(destination)

    os.makedirs(destination, exist_ok=False)
    manifest = _sanitize_manifest(bundle["manifest"])
    write_json_file(os.path.join(destination, "manifest.json"), manifest)
    write_json_file(os.path.join(destination, "summary.json"), _sanitize_dataset_paths(bundle["summary"]))
    write_json_file(os.path.join(destination, "records.json"), bundle["records"])
    write_json_file(
        os.path.join(destination, "showcase.json"),
        {
            "showcase_id": safe_id,
            "title": title.strip() or safe_id.replace("_", " ").replace("-", " ").title(),
            "description": description.strip(),
        },
    )
    return destination


def _discover_bundle_dirs(root: str) -> list[str]:
    if not os.path.isdir(root):
        return []
    bundle_dirs = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name.lower() != "latest"]
        if all(filename in filenames for filename in BENCHMARK_FILENAMES):
            bundle_dirs.append(current)
            dirnames[:] = []
    return bundle_dirs


def _validate_bundle(bundle: dict[str, Any]) -> None:
    if not isinstance(bundle.get("manifest"), dict):
        raise TypeError("Benchmark manifest must be an object.")
    if not isinstance(bundle.get("summary"), dict):
        raise TypeError("Benchmark summary must be an object.")
    if not isinstance(bundle.get("records"), list):
        raise TypeError("Benchmark records must be a list.")


def _bundle_identity(bundle: dict[str, Any]) -> tuple[Any, ...]:
    manifest = bundle["manifest"]
    dataset = manifest.get("dataset") or {}
    return (
        manifest.get("timestamp"),
        dataset.get("dataset_fingerprint") or manifest.get("dataset_id"),
        tuple(manifest.get("models") or []),
        tuple(manifest.get("campaign_ids") or []),
        tuple(manifest.get("character_ids") or []),
        tuple(manifest.get("presets") or []),
    )


def _read_optional_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file_obj:
        value = json.load(file_obj)
    return value if isinstance(value, dict) else {}


def _safe_showcase_id(showcase_id: str) -> str:
    normalized = showcase_id.strip()
    if not normalized or normalized in {".", ".."}:
        raise ValueError("Showcase ID must be non-empty.")
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in normalized):
        raise ValueError("Showcase ID may contain only letters, numbers, underscores, and hyphens.")
    return normalized


def _sanitize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_dataset_paths(manifest)
    sanitized.pop("data_dir", None)
    return sanitized


def _sanitize_dataset_paths(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    dataset = dict(sanitized.get("dataset") or {})
    dataset.pop("data_dir", None)
    dataset.pop("runtime_data_dir", None)
    sanitized["dataset"] = dataset
    return sanitized
