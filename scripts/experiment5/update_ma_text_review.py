from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_PATH = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "experiment5_dev50_20260504_r5_ma_text_ocr_review"
    / "inputs"
    / "gold_ma_text_dev50_ocr_review_template.jsonl"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update one Experiment 5 MA_TEXT human review row.")
    parser.add_argument("chart_id")
    parser.add_argument("reviewed_gold_ma_prose")
    parser.add_argument("--review-path", type=Path, default=DEFAULT_REVIEW_PATH)
    parser.add_argument("--status", default="reviewed_accept", choices=["reviewed_accept", "needs_discussion", "reviewed_reject"])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    rows = read_jsonl(args.review_path)
    updated = False
    for row in rows:
        if row.get("chart_id") == args.chart_id:
            row["reviewed_gold_ma_prose"] = args.reviewed_gold_ma_prose
            row["review_status"] = args.status
            row["review_notes"] = args.notes
            updated = True
            break
    if not updated:
        raise SystemExit(f"chart_id not found: {args.chart_id}")
    write_jsonl(args.review_path, rows)
    print(json.dumps({"updated": args.chart_id, "review_path": str(args.review_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
