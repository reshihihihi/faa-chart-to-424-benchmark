import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


TRACKED_PATH_KEYS = [
    "formal_manifest",
    "canonical_targets_dir",
    "group1_formal_split",
    "group1_formal_scoring_manifest",
    "base_vlm_model_dir",
    "d1_lora_or_checkpoint_dir",
    "evidence_to_semantics_train_jsonl",
    "evidence_to_semantics_dev_jsonl",
    "evidence_to_semantics_eval_jsonl",
    "chart_to_evidence_train_jsonl",
    "chart_to_evidence_dev_jsonl",
    "chart_to_evidence_eval_jsonl",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize_path(value: str):
    p = Path(value)
    item = {"path": value, "exists": p.exists()}
    if not p.exists():
        return item
    if p.is_file():
        item.update({"kind": "file", "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    elif p.is_dir():
        files = [x for x in p.rglob("*") if x.is_file()]
        item.update({"kind": "directory", "file_count": len(files)})
    return item


def main():
    parser = argparse.ArgumentParser(description="Write a reproducibility manifest for Group 1 SFT extension runs.")
    parser.add_argument("--paths", required=True, help="Path to local_paths.local.json")
    parser.add_argument("--out", required=True, help="Output manifest JSON path")
    args = parser.parse_args()

    paths_file = Path(args.paths)
    config = load_json(paths_file)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "group1_sft_run_manifest_v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paths_file": str(paths_file),
        "method_set_config": "training/group1_sft/configs/group1_sft_method_set.json",
        "tracked_paths": {
            key: summarize_path(config[key])
            for key in TRACKED_PATH_KEYS
            if config.get(key) and "CHANGE_ME" not in config[key]
        },
        "notes": [
            "This manifest records local file presence and hashes where practical.",
            "Large model directories are summarized by file count only.",
            "Do not commit local paths, secrets, checkpoints, or large raw outputs."
        ],
    }
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "tracked_path_count": len(manifest["tracked_paths"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
