from __future__ import annotations

import json
import re
import sys
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "docs/migration_protocol.md",
    "docs/no_leakage_policy.md",
    "docs/repository_governance.md",
    "docs/rerun_policy.md",
    "docs/formal_freeze_checklist.md",
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
        if freeze.get("status") in {"formal_frozen", "evaluation_ready"}:
            errors.extend(check_formal_freeze_requirements(freeze))

    if not isinstance(provenance, dict):
        errors.append("upstream_provenance_manifest.json must be an object")
    else:
        if provenance.get("source_repo") != "reshihihihi/faa-missed-approach-experiment":
            errors.append("provenance source_repo must point to the upstream experiment repo")
        if "imports" not in provenance or not isinstance(provenance["imports"], list):
            errors.append("provenance manifest must contain an imports list")
        else:
            errors.extend(check_provenance_imports(provenance["imports"]))
    errors.extend(check_prompt_manifest())
    errors.extend(check_model_manifest())

    return errors


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def is_commit_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40}", value) is not None


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_provenance_imports(imports: list[object]) -> list[str]:
    errors: list[str] = []
    allowed_statuses = {"planned", "imported", "superseded", "rejected"}
    for index, item in enumerate(imports):
        prefix = f"provenance imports[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        status = item.get("status")
        if status not in allowed_statuses:
            errors.append(f"{prefix} has invalid status: {status!r}")
        if item.get("source_commit") is not None and not is_commit_sha(item.get("source_commit")):
            errors.append(f"{prefix} source_commit must be a 40-char commit SHA")
        for key in ["source_paths", "destination_paths"]:
            if key not in item or not isinstance(item[key], list) or not item[key]:
                errors.append(f"{prefix} missing non-empty {key}")
        if status == "imported" or item.get("frozen_for_formal_evaluation") is True:
            if not is_sha256(item.get("sha256")):
                errors.append(f"{prefix} imported/frozen asset must have sha256")
            for dest in item.get("destination_paths", []):
                dest_path = ROOT / str(dest)
                if not dest_path.exists():
                    errors.append(f"{prefix} destination does not exist: {dest}")
    return errors


def check_prompt_manifest() -> list[str]:
    errors: list[str] = []
    manifest = read_json(ROOT / "configs/prompt_manifest.json")
    if not isinstance(manifest, dict):
        return ["prompt_manifest.json must be an object"]
    prompts = manifest.get("prompts")
    if not isinstance(prompts, list):
        return ["prompt_manifest.json prompts must be a list"]
    for index, prompt in enumerate(prompts):
        prefix = f"prompt_manifest prompts[{index}]"
        if not isinstance(prompt, dict):
            errors.append(f"{prefix} must be an object")
            continue
        path_value = prompt.get("prompt_path")
        hash_value = prompt.get("sha256")
        if path_value is None:
            errors.append(f"{prefix} missing prompt_path")
            continue
        path = ROOT / str(path_value)
        if not path.is_file():
            errors.append(f"{prefix} path does not exist: {path_value}")
            continue
        if not is_sha256(hash_value):
            errors.append(f"{prefix} must include sha256")
        elif file_sha256(path).lower() != str(hash_value).lower():
            errors.append(f"{prefix} sha256 mismatch for {path_value}")
        for key in ["allowed_input_fields", "forbidden_input_fields"]:
            if key not in prompt or not isinstance(prompt[key], list):
                errors.append(f"{prefix} missing list field: {key}")
    return errors


def check_model_manifest() -> list[str]:
    errors: list[str] = []
    manifest = read_json(ROOT / "configs/model_config_manifest.json")
    if not isinstance(manifest, dict):
        return ["model_config_manifest.json must be an object"]
    models = manifest.get("models")
    if not isinstance(models, list):
        return ["model_config_manifest.json models must be a list"]
    forbidden_keys = {"token", "api_key", "auth_token", "secret", "password"}
    for index, model in enumerate(models):
        prefix = f"model_config_manifest models[{index}]"
        if not isinstance(model, dict):
            errors.append(f"{prefix} must be an object")
            continue
        lower_keys = {str(key).lower() for key in model}
        if forbidden_keys & lower_keys:
            errors.append(f"{prefix} contains forbidden secret-like key")
        for key in ["provider", "model", "temperature", "max_tokens"]:
            if key not in model:
                errors.append(f"{prefix} missing {key}")
    return errors


def check_formal_freeze_requirements(freeze: dict) -> list[str]:
    errors: list[str] = []
    if freeze.get("schema", {}).get("status") != "frozen":
        errors.append("formal freeze requires schema.status=frozen")
    if not is_sha256(freeze.get("schema", {}).get("sha256")):
        errors.append("formal freeze requires schema.sha256")
    data = freeze.get("data", {})
    if data.get("status") != "frozen":
        errors.append("formal freeze requires data.status=frozen")
    if data.get("formal_evaluation_split_locked") is not True:
        errors.append("formal freeze requires formal_evaluation_split_locked=true")
    for key in ["manifest_path", "sample_manifest_path", "splits_path", "checksums_path"]:
        value = data.get(key)
        if not value or not (ROOT / value).exists():
            errors.append(f"formal freeze requires existing data.{key}")
    for key in ["methods", "models", "prompts", "parser_repair", "scorer", "rerun_policy"]:
        section = freeze.get(key, {})
        if isinstance(section, dict) and section.get("status") not in {"frozen", "locked"}:
            errors.append(f"formal freeze requires {key}.status frozen/locked")
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
