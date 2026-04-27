from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "docs/migration_protocol.md",
    "docs/no_leakage_policy.md",
    "docs/rerun_policy.md",
    "configs/frozen_experiment_manifest.json",
    "configs/model_config_manifest.json",
    "configs/prompt_manifest.json",
    "configs/parser_repair_policy.md",
    "metadata/upstream_provenance_manifest.json",
    "benchmark_exports/derived/v2/README.md",
]

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".json",
    ".jsonl",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
}

SECRET_PATTERNS = [
    re.compile(r"ck_[A-Za-z0-9]{20,}"),
    re.compile(r"gh[opsu]_[A-Za-z0-9_]{20,}"),
    re.compile(r"ANTHROPIC_AUTH_TOKEN\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{20,}", re.I),
    re.compile(r"ANTHROPIC_API_KEY\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{20,}", re.I),
]

DRIVE_PATTERN = r"\b[A-Za-z]" + r":\\"
SLASH_DRIVE_PATTERN = r"\b/" + "E" + r":/"
LOCAL_PATH_PATTERNS = [
    re.compile(DRIVE_PATTERN),
    re.compile(SLASH_DRIVE_PATTERN, re.I),
]


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"{path.relative_to(ROOT)} is not valid JSON: {exc}") from exc


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def check_required_files() -> list[str]:
    errors = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")
    return errors


def check_json_files() -> list[str]:
    errors = []
    for path in iter_text_files():
        if path.suffix.lower() != ".json":
            continue
        try:
            read_json(path)
        except AssertionError as exc:
            errors.append(str(exc))
    return errors


def check_secrets_and_paths() -> list[str]:
    errors = []
    for path in iter_text_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {rel}")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                errors.append(f"local absolute path in {rel}")
    return errors


def check_manifest_shape() -> list[str]:
    errors = []
    freeze = read_json(ROOT / "configs/frozen_experiment_manifest.json")
    provenance = read_json(ROOT / "metadata/upstream_provenance_manifest.json")

    if not isinstance(freeze, dict):
        errors.append("frozen_experiment_manifest.json must be an object")
    else:
        for key in [
            "schema",
            "data",
            "methods",
            "models",
            "prompts",
            "parser_repair",
            "scorer",
            "rerun_policy",
        ]:
            if key not in freeze:
                errors.append(f"frozen_experiment_manifest.json missing key: {key}")

    if not isinstance(provenance, dict):
        errors.append("upstream_provenance_manifest.json must be an object")
    else:
        if provenance.get("source_repo") != "reshihihihi/faa-missed-approach-experiment":
            errors.append("provenance source_repo must point to the upstream experiment repo")
        if "imports" not in provenance or not isinstance(provenance["imports"], list):
            errors.append("provenance manifest must contain an imports list")

    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(check_required_files())
    errors.extend(check_json_files())
    errors.extend(check_secrets_and_paths())
    errors.extend(check_manifest_shape())

    if errors:
        print("Repository integrity check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
