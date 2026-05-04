from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_QUEUE = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "experiment5_dev50_20260504_r5_ma_text_ocr_review"
    / "inputs"
    / "gold_ma_text_dev50_ocr_review_queue.jsonl"
)
DEFAULT_OUT_DIR = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "experiment5_dev50_20260504_r5_ma_text_ocr_review"
)


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


def normalize(text: str) -> str:
    text = text.replace("掳", "°")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"MISSED\s+APPROACH\s*[:.]*", "MISSED APPROACH:", text, flags=re.IGNORECASE)
    text = re.sub(r"MISSED APPROACH:\s*", "MISSED APPROACH: ", text)
    return text.strip()


def trim_to_missed_approach(text: str) -> str:
    text = normalize(text)
    match = re.search(r"\bMISSED\s+APPROACH\s*[:.]*\s*(.*)", text, flags=re.IGNORECASE)
    if not match:
        return "MISSED APPROACH: " + text
    return normalize("MISSED APPROACH: " + match.group(1).strip())


def suspicious_flags(text: str) -> list[str]:
    flags: list[str] = []
    checks = {
        "contains_lpv_or_lnav_minima_text": r"\b(LPV|LNAV/VNAV|LNAV|MDA|DA)\b",
        "contains_weather_or_temperature_note": r"(Baro|temperature|below|SM NA|NA\.)",
        "contains_common_ocr_garbage": r"(鈥|掳|hola|ircling|rease|\bAs AO\b)",
        "missing_climb_keyword": r"^((?!\bClimb(?:ing)?\b).)*$",
        "missing_terminal_punctuation": r"[^.!?]$",
    }
    for name, pattern in checks.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            flags.append(name)
    return flags


def render_report(rows: list[dict[str, Any]]) -> str:
    flagged = [row for row in rows if row["suspicious_flags"]]
    lines = [
        "# Experiment 5 MA_TEXT auto-trimmed input report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## 说明",
        "",
        "本文件把 OCR 候选统一裁剪到 `MISSED APPROACH:` 开头，删除此前的灯光、minima、温度等前缀污染。",
        "",
        "这一步只能降低前缀污染，不能保证 OCR 后半句完全正确。因此当前状态是 provisional，不等于人工 reviewed gold。",
        "",
        "## 汇总",
        "",
        f"- rows: {len(rows)}",
        f"- suspicious rows: {len(flagged)}",
        "",
    ]
    if flagged:
        lines.append("## 需要重点抽查")
        lines.append("")
        for row in flagged[:50]:
            lines.append(f"- `{row['chart_id']}` flags={row['suspicious_flags']}")
            lines.append("")
            lines.append("```text")
            lines.append(row["gold_ma_prose"])
            lines.append("```")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build provisional MA text input by trimming OCR to MISSED APPROACH.")
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_rows: list[dict[str, Any]] = []
    for row in read_jsonl(args.review_queue):
        source = row.get("ocr_missed_approach_candidate") or row.get("ocr_text_candidate") or row.get("pdf_missed_approach_candidate") or ""
        prose = trim_to_missed_approach(str(source))
        out_rows.append(
            {
                "schema_version": "experiment5_ma_text_auto_trimmed_provisional_v1",
                "chart_id": row["chart_id"],
                "gold_ma_prose": prose,
                "review_status": "auto_trimmed_from_ocr_needs_spotcheck",
                "suspicious_flags": suspicious_flags(prose),
                "source": "admin_ma_text_crop_tesseract_ocr_trimmed_to_missed_approach",
                "source_queue_path": str(args.review_queue),
                "source_crop_image_path": row.get("crop_image_path"),
                "ocr_selected_psm": row.get("selected_ocr_psm"),
                "ocr_mean_confidence": row.get("selected_ocr_mean_confidence"),
                "notes": "Provisional only: prefix before MISSED APPROACH removed; not human reviewed.",
                "source_contract": {
                    "allows_chart_crop_pixels": True,
                    "allows_ocr_text": True,
                    "allows_final_answer": False,
                    "allows_canonical_target": False,
                    "derived_from_final_answer": False,
                },
            }
        )

    input_path = args.out_dir / "inputs" / "gold_ma_text_dev50_ocr_auto_trimmed_provisional.jsonl"
    report_path = args.out_dir / "reports" / "ma_text_auto_trimmed_provisional_report_zh.md"
    summary_path = args.out_dir / "reports" / "ma_text_auto_trimmed_provisional_summary.json"
    write_jsonl(input_path, out_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(out_rows), encoding="utf-8")
    write_json(
        summary_path,
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "rows": len(out_rows),
            "input_path": str(input_path),
            "report_path": str(report_path),
            "review_status": "auto_trimmed_from_ocr_needs_spotcheck",
            "suspicious_rows": sum(1 for row in out_rows if row["suspicious_flags"]),
            "ready_as_reviewed_gold": False,
        },
    )
    print(json.dumps({"rows": len(out_rows), "input_path": str(input_path), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
