import argparse
import json
from pathlib import Path


REQUIRED_KEYS = [
    "local_root",
    "repo_root",
    "formal_manifest",
    "formal_images_dir",
    "canonical_targets_dir",
    "group1_formal_split",
    "group1_formal_scoring_manifest",
    "base_vlm_model_dir",
    "d1_lora_or_checkpoint_dir",
    "output_root",
    "reports_dir",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description="Validate local paths for Group 1 SFT extension runs.")
    parser.add_argument("--paths", required=True, help="Path to local_paths.local.json")
    args = parser.parse_args()

    path_file = Path(args.paths)
    config = load_json(path_file)

    missing_keys = [key for key in REQUIRED_KEYS if not config.get(key)]
    checks = []
    for key, value in config.items():
        if not isinstance(value, str) or not value:
            continue
        if "CHANGE_ME" in value:
            checks.append({"key": key, "path": value, "status": "needs_edit"})
            continue
        p = Path(value)
        checks.append({"key": key, "path": value, "exists": p.exists(), "status": "ok" if p.exists() else "missing"})

    failed = missing_keys or any(row["status"] in {"needs_edit", "missing"} for row in checks if row["key"] in REQUIRED_KEYS)
    report = {
        "paths_file": str(path_file),
        "missing_required_keys": missing_keys,
        "checks": checks,
        "ready": not failed,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
