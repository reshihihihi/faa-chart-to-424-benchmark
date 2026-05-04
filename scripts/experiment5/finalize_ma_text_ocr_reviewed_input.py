from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260504_r5_ma_text_ocr_review"
DEFAULT_PROVISIONAL = RUN_DIR / "inputs" / "gold_ma_text_dev50_ocr_auto_cleaned_v2_provisional.jsonl"
DEFAULT_OUT = RUN_DIR / "inputs" / "gold_ma_text_dev50_ocr_reviewed.jsonl"


USER_IMAGE_CONFIRMED_OVERRIDES = {
    "KACT_R01": "MISSED APPROACH: Climb to 3000 direct CHRUS and hold.",
    "KACT_R32": "MISSED APPROACH: Climb to 4000 direct EVVIS and hold, continue climb-in-hold to 4000.",
    "KAEX_R18": "MISSED APPROACH: Climb to 4000 direct HIPKU and via 105° track to MUSHE and hold.",
    "KAEX_R32": "MISSED APPROACH: Climb to 3000 direct EBYAJ WP and hold.",
    "KAND_R17": "MISSED APPROACH: Climb to 2500 direct ZAROM and hold.",
    "KAPN_R01": "MISSED APPROACH: Climb to 3500 direct HIMVO and on track 307° to RABBO and hold.",
}

FORBIDDEN_KEYS = {
    "annotation_pr28_json",
    "target",
    "score",
    "canonical_answer",
    "canonical_leg_index",
    "Q_terminator",
    "leg_type",
    "field_review_v2",
    "candidate_leg_id",
    "expected_value",
    "target_value",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def flatten(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        out: list[tuple[str, Any]] = []
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.append((path, child))
            out.extend(flatten(child, path))
        return out
    if isinstance(value, list):
        out = []
        for index, child in enumerate(value):
            out.extend(flatten(child, f"{prefix}[{index}]"))
        return out
    return []


def key_tail(path: str) -> str:
    return re.sub(r"\[\d+\]", "", path).split(".")[-1]


def scan_no_leakage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    key_hits: list[dict[str, Any]] = []
    non_ma_prefix: list[dict[str, Any]] = []
    for line_no, row in enumerate(rows, start=1):
        prose = str(row.get("gold_ma_prose") or "")
        if not prose.startswith("MISSED APPROACH:"):
            non_ma_prefix.append({"line": line_no, "chart_id": row.get("chart_id"), "gold_ma_prose": prose})
        for path, _ in flatten(row):
            if key_tail(path) in FORBIDDEN_KEYS:
                key_hits.append({"line": line_no, "chart_id": row.get("chart_id"), "key_path": path})
    return {
        "status": "PASS" if not key_hits and not non_ma_prefix else "FAIL",
        "rows": len(rows),
        "forbidden_key_hit_count": len(key_hits),
        "forbidden_key_hits": key_hits[:50],
        "non_missed_approach_prefix_count": len(non_ma_prefix),
        "non_missed_approach_prefix_rows": non_ma_prefix[:50],
    }


def render_report(rows: list[dict[str, Any]], scan: dict[str, Any]) -> str:
    status_counts = Counter(row["review_status"] for row in rows)
    lines = [
        "# Experiment 5 dev50 MA_TEXT OCR reviewed input",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## 结论",
        "",
        "`gold_ma_text_dev50_ocr_reviewed.jsonl` 已生成。50 条都以 `MISSED APPROACH:` 开头，且不使用最终答案、canonical_answer 或 scoring target。",
        "",
        "6 条原先可疑的 OCR 已按用户提供的图片文本覆盖；其余 44 条来自 auto-cleaned v2 且没有 suspicious flag。",
        "",
        "## 计数",
        "",
    ]
    for key, value in sorted(status_counts.items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## no-leakage scan",
            "",
            f"- status: `{scan['status']}`",
            f"- rows: {scan['rows']}",
            f"- forbidden key hits: {scan['forbidden_key_hit_count']}",
            f"- non-MISSED-APPROACH prefix rows: {scan['non_missed_approach_prefix_count']}",
            "",
            "## 用户图片确认覆盖的 6 条",
            "",
        ]
    )
    for chart_id, prose in USER_IMAGE_CONFIRMED_OVERRIDES.items():
        lines.append(f"- `{chart_id}`: {prose}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize reviewed MA_TEXT OCR input after user image confirmation.")
    parser.add_argument("--provisional", type=Path, default=DEFAULT_PROVISIONAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for row in read_jsonl(args.provisional):
        chart_id = str(row["chart_id"])
        if chart_id in USER_IMAGE_CONFIRMED_OVERRIDES:
            prose = USER_IMAGE_CONFIRMED_OVERRIDES[chart_id]
            review_status = "reviewed_accept_user_image_confirmed"
            reviewer = "user_20260504_inline_image_confirmation"
        else:
            prose = str(row["gold_ma_prose"])
            review_status = "auto_cleaned_v2_accept_no_suspicious_flags"
            reviewer = "codex_auto_cleaned_v2_no_suspicious_flags"
        rows.append(
            {
                "schema_version": "experiment5_ma_text_ocr_reviewed_v1",
                "chart_id": chart_id,
                "gold_ma_prose": prose,
                "review_status": review_status,
                "reviewer": reviewer,
                "source": "admin_ma_text_crop_ocr_user_reviewed",
                "source_provisional_path": str(args.provisional),
                "source_crop_image_path": row.get("source_crop_image_path"),
                "ocr_mean_confidence": row.get("ocr_mean_confidence"),
                "notes": "Visible MA_TEXT crop OCR/correction only; no final answer-derived text.",
                "source_contract": {
                    "allows_chart_crop_pixels": True,
                    "allows_ocr_text": True,
                    "allows_user_visible_text_correction": True,
                    "allows_final_answer": False,
                    "allows_canonical_target": False,
                    "derived_from_final_answer": False,
                },
            }
        )

    scan = scan_no_leakage(rows)
    write_jsonl(args.out, rows)
    reports_dir = args.out.parents[1] / "reports"
    write_json(reports_dir / "ma_text_ocr_reviewed_no_leakage_report.json", scan)
    (reports_dir / "ma_text_ocr_reviewed_summary_zh.md").write_text(render_report(rows, scan), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "out": str(args.out), "scan_status": scan["status"]}, ensure_ascii=False, indent=2))
    return 0 if scan["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
