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
DEGREE = "\u00b0"


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
    text = text.replace("掳", DEGREE)
    text = text.replace("\u00a9", "")
    text = text.replace("\u2014", " ")
    text = text.replace("鈥?", " ")
    text = text.replace("鈥榺", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"MISSED\s+APPROACH\s*[:.]*", "MISSED APPROACH:", text, flags=re.IGNORECASE)
    text = re.sub(r"MISSED APPROACH:\s*", "MISSED APPROACH: ", text)
    text = re.sub(r"\s+([.,])", r"\1", text)
    return text.strip()


def trim_to_missed_approach(text: str) -> str:
    text = normalize(text)
    match = re.search(r"\bMISSED\s+APPROACH\s*[:.]*\s*(.*)", text, flags=re.IGNORECASE)
    if not match:
        return normalize("MISSED APPROACH: " + text)
    return normalize("MISSED APPROACH: " + match.group(1).strip())


def cut_to_first_climb_when_prefix_is_noisy(text: str) -> str:
    match = re.match(r"^(MISSED APPROACH:\s*)(.*)$", text, flags=re.IGNORECASE)
    if not match:
        return text
    prefix, tail = match.groups()
    climb = re.search(r"\bClimb(?:ing)?\b", tail, flags=re.IGNORECASE)
    if not climb:
        return text
    before_climb = tail[: climb.start()]
    if re.search(r"\b(LPV|LNAV|MDA|DA|Baro|visibility|Cats|SM|feet|When)\b", before_climb, flags=re.IGNORECASE):
        return normalize(prefix + tail[climb.start() :])
    return text


def ensure_terminal_punctuation(text: str) -> str:
    text = text.strip()
    if text and text[-1] not in ".!?":
        return text + "."
    return text


def clean_known_ocr_noise(text: str) -> str:
    text = cut_to_first_climb_when_prefix_is_noisy(text)

    text = re.sub(r"\bhola\b", "hold", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLold\b", "hold", text, flags=re.IGNORECASE)
    text = re.sub(r"\bClimb\s+F\)\.\s+to\b", "Climb to", text, flags=re.IGNORECASE)

    # Cases where OCR kept minima or visibility words between "direct" and the real fix.
    direct_hold = re.search(
        r"\bClimb(?:ing)?\s+to\s+(?P<alt>\d{3,5})\s+direct\s+(?P<middle>.*?)\b(?P<fix>[A-Z][A-Z0-9]{2,6})\s+and\s+hold\b",
        text,
        flags=re.IGNORECASE,
    )
    if direct_hold:
        middle = direct_hold.group("middle")
        if re.search(r"\b(LPV|LNAV|MDA|DA|feet|SM|As AO)\b", middle, flags=re.IGNORECASE):
            text = re.sub(
                r"\bClimb(?:ing)?\s+to\s+\d{3,5}\s+direct\s+.*?\b[A-Z][A-Z0-9]{2,6}\s+and\s+hold\b",
                f"Climb to {direct_hold.group('alt')} direct {direct_hold.group('fix')} and hold",
                text,
                count=1,
                flags=re.IGNORECASE,
            )

    # Cases where OCR kept "Circling", "NAV", or local chart-name fragments before/after the real fix.
    text = re.sub(r"\brease\s+(?=Climb\b)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdirect\s+(?:and\s+)?(?:-?ircling\s+|Circling\s+|NAV\s+)+([A-Z][A-Z0-9]{2,6})\s+and\s+hold\b", r"direct \1 and hold", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNAV\s+(?=continue\s+climb-in-hold\b)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcontinue\s+climb-in-hold\s+.*?\bto\s+(\d{3,5})\b", r"continue climb-in-hold to \1", text, flags=re.IGNORECASE)

    # Cases where a long visibility/minima fragment sits between "direct" and the on-track fix.
    track_hold = re.search(
        rf"\bClimb\s+to\s+(?P<alt>\d{{3,5}})\s+direct\s+.*?\b(?P<fix>[A-Z][A-Z0-9]{{2,6}})\s+and\s+on\s+track\s+.*?(?P<deg>\d{{3}})\s*{re.escape(DEGREE)}?\s+to\s+(?P<tofix>[A-Z][A-Z0-9]{{2,6}})\s+and\s+hold\b",
        text,
        flags=re.IGNORECASE,
    )
    if track_hold and re.search(r"\b(SM|visibility|When|feet|inop)\b", text, flags=re.IGNORECASE):
        text = (
            "MISSED APPROACH: "
            f"Climb to {track_hold.group('alt')} direct {track_hold.group('fix')} "
            f"and on track {track_hold.group('deg')}{DEGREE} to {track_hold.group('tofix')} and hold."
        )

    # Cases where visibility notes were inserted inside a simple direct-to-hold instruction.
    simple_direct_hold = re.search(
        r"\bClimb\s+.*?\bto\s+(?P<alt>\d{3,5})\s+direct\s+(?P<fix>[A-Z][A-Z0-9]{2,6})\s+.*?\bhold\b",
        text,
        flags=re.IGNORECASE,
    )
    if (
        simple_direct_hold
        and not re.search(r"\bon\s+track\b", text, flags=re.IGNORECASE)
        and re.search(r"\b(visibility|ity Amie|ter visibility)\b", text, flags=re.IGNORECASE)
    ):
        text = f"MISSED APPROACH: Climb to {simple_direct_hold.group('alt')} direct {simple_direct_hold.group('fix')} and hold."

    text = normalize(text)
    return ensure_terminal_punctuation(text)


def build_cleaned_prose(row: dict[str, Any]) -> tuple[str, str]:
    source_kind = "ocr_missed_approach_candidate"
    source = str(row.get(source_kind) or "")
    if not source.strip():
        source_kind = "ocr_text_candidate"
        source = str(row.get(source_kind) or "")
    if not source.strip():
        source_kind = "pdf_missed_approach_candidate"
        source = str(row.get(source_kind) or "")
    prose = clean_known_ocr_noise(trim_to_missed_approach(source))
    return prose, source_kind


def suspicious_flags(text: str) -> list[str]:
    flags: list[str] = []
    checks = {
        "contains_lpv_or_lnav_minima_text": r"\b(LPV|LNAV/VNAV|LNAV|MDA|DA)\b",
        "contains_weather_or_visibility_note": r"\b(Baro|temperature|below|SM NA|visibility|Cats|When|inop)\b",
        "contains_common_ocr_garbage": r"(hola|Lold|ircling|rease|\bAs AO\b|ity Amie|Mc Gregor|鈥|\u00a9)",
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
        "# Experiment 5 MA_TEXT auto-cleaned v2 provisional input report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This v2 file applies extra OCR cleanup after trimming to MISSED APPROACH.",
        "It removes noisy prefixes before the first Climb/Climbing phrase, fixes common OCR hold/degree errors,",
        "and repairs six rows that were flagged by the first provisional pass.",
        "",
        "The source is still chart crop OCR/PDF text-layer candidates only; final answers are not used.",
        "Status remains provisional until human spotcheck or acceptance.",
        "",
        f"- rows: {len(rows)}",
        f"- suspicious rows: {len(flagged)}",
        "",
    ]
    if flagged:
        lines.extend(["## Remaining rows to inspect", ""])
        for row in flagged[:50]:
            lines.append(f"- `{row['chart_id']}` flags={row['suspicious_flags']}")
            lines.append("")
            lines.append("```text")
            lines.append(row["gold_ma_prose"])
            lines.append("```")
            lines.append("")
    else:
        lines.append("No rows were flagged by the automatic suspicious-pattern scanner.")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build provisional MA text input by trimming and cleaning OCR.")
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_rows: list[dict[str, Any]] = []
    for row in read_jsonl(args.review_queue):
        prose, source_kind = build_cleaned_prose(row)
        out_rows.append(
            {
                "schema_version": "experiment5_ma_text_auto_cleaned_v2_provisional_v1",
                "chart_id": row["chart_id"],
                "gold_ma_prose": prose,
                "review_status": "auto_cleaned_from_ocr_needs_spotcheck",
                "suspicious_flags": suspicious_flags(prose),
                "source": "admin_ma_text_crop_tesseract_ocr_trimmed_and_cleaned_v2",
                "source_queue_path": str(args.review_queue),
                "source_crop_image_path": row.get("crop_image_path"),
                "source_text_field": source_kind,
                "ocr_selected_psm": row.get("selected_ocr_psm"),
                "ocr_mean_confidence": row.get("selected_ocr_mean_confidence"),
                "notes": "Provisional only: automatic OCR cleanup; not final-answer-derived and not human reviewed.",
                "source_contract": {
                    "allows_chart_crop_pixels": True,
                    "allows_ocr_text": True,
                    "allows_pdf_text_layer_candidate_for_fallback": True,
                    "allows_final_answer": False,
                    "allows_canonical_target": False,
                    "derived_from_final_answer": False,
                },
            }
        )

    input_path = args.out_dir / "inputs" / "gold_ma_text_dev50_ocr_auto_cleaned_v2_provisional.jsonl"
    report_path = args.out_dir / "reports" / "ma_text_auto_cleaned_v2_provisional_report.md"
    summary_path = args.out_dir / "reports" / "ma_text_auto_cleaned_v2_provisional_summary.json"
    write_jsonl(input_path, out_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(out_rows) + "\n", encoding="utf-8")
    write_json(
        summary_path,
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "rows": len(out_rows),
            "input_path": str(input_path),
            "report_path": str(report_path),
            "review_status": "auto_cleaned_from_ocr_needs_spotcheck",
            "suspicious_rows": sum(1 for row in out_rows if row["suspicious_flags"]),
            "ready_as_reviewed_gold": False,
            "final_answer_used": False,
        },
    )
    print(
        json.dumps(
            {"rows": len(out_rows), "input_path": str(input_path), "report_path": str(report_path)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
