from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_DEV50_MANIFEST = DEFAULT_RUN_DIR / "manifests" / "dev50_chart_manifest.jsonl"
DEFAULT_SANITIZED_REGIONS = DEFAULT_RUN_DIR / "inputs" / "admin_regions_sanitized_dev50.jsonl"


@dataclass(frozen=True)
class Word:
    text: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def x_mid(self) -> float:
        return (self.x_min + self.x_max) / 2.0

    @property
    def y_mid(self) -> float:
        return (self.y_min + self.y_max) / 2.0


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + ("\n" if value and not value.endswith("\n") else ""), encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def download_pdf(url: str, out_path: Path, retries: int = 3) -> tuple[bool, str | None]:
    if out_path.exists() and out_path.stat().st_size > 0:
        return True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "experiment5-dev50/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                out_path.write_bytes(response.read())
            if out_path.stat().st_size > 0:
                return True, None
            last_error = "downloaded empty file"
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(min(2 * attempt, 5))
    return False, last_error


def run_pdftotext(pdf_path: Path, bbox_path: Path, layout_path: Path) -> tuple[bool, str | None]:
    bbox_path.parent.mkdir(parents=True, exist_ok=True)
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["pdftotext", "-bbox", str(pdf_path), str(bbox_path)], check=True, capture_output=True, text=True)
        subprocess.run(
            ["pdftotext", "-layout", "-nopgbrk", str(pdf_path), str(layout_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return False, str(exc)
    return True, None


def parse_bbox_words(path: Path) -> tuple[float | None, float | None, list[Word]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    page_match = re.search(r'<page\s+width="([0-9.]+)"\s+height="([0-9.]+)"', text)
    page_width = float(page_match.group(1)) if page_match else None
    page_height = float(page_match.group(2)) if page_match else None
    words: list[Word] = []
    pattern = re.compile(
        r'<word\s+xMin="([0-9.]+)"\s+yMin="([0-9.]+)"\s+xMax="([0-9.]+)"\s+yMax="([0-9.]+)">(.+?)</word>'
    )
    for match in pattern.finditer(text):
        raw = html.unescape(match.group(5)).strip()
        if not raw:
            continue
        words.append(
            Word(
                text=raw,
                x_min=float(match.group(1)),
                y_min=float(match.group(2)),
                x_max=float(match.group(3)),
                y_max=float(match.group(4)),
            )
        )
    return page_width, page_height, words


def words_to_lines(words: list[Word]) -> str:
    if not words:
        return ""
    sorted_words = sorted(words, key=lambda word: (word.y_mid, word.x_mid))
    lines: list[list[Word]] = []
    for word in sorted_words:
        if not lines or abs(lines[-1][-1].y_mid - word.y_mid) > 3.0:
            lines.append([word])
        else:
            lines[-1].append(word)
    text_lines = [" ".join(item.text for item in sorted(line, key=lambda word: word.x_mid)) for line in lines]
    return "\n".join(text_lines)


def clean_spacing(text: str) -> str:
    text = text.replace("º", "°").replace("˚", "°")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"\bAPPROACH\s*:\s*", "APPROACH: ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMISSED\s+APCH\b", "MISSED APPROACH", text, flags=re.IGNORECASE)
    return text


def trim_to_missed_approach_instruction(text: str) -> str:
    text = clean_spacing(text)
    match = re.search(r"\bMISSED\s+APPROACH\b\s*:?", text, flags=re.IGNORECASE)
    if match:
        text = "MISSED APPROACH:" + text[match.end() :].lstrip(" :")
    else:
        approach = re.search(r"\bAPPROACH\b\s*:?", text, flags=re.IGNORECASE)
        if approach:
            text = "MISSED " + text[approach.start() :]
    terminal_patterns = [
        r"\bhold,\s*continue\s+climb-in-hold\s+to\s+[0-9]{3,5}\s*\.?",
        r"\bhold\.\s*Continue\s+climb-in-hold\s+to\s+[0-9]{3,5}\s*\.?",
        r"\bhold\s*,?\s*continue\s+climb\s+in\s+hold\s+to\s+[0-9]{3,5}\s*\.?",
        r"\bhold\s*\.?",
    ]
    ends: list[int] = []
    for pattern in terminal_patterns:
        for item in re.finditer(pattern, text, flags=re.IGNORECASE):
            ends.append(item.end())
    if ends:
        text = text[: max(ends)]
    elif "." in text:
        text = text[: text.find(".") + 1]
    text = re.sub(r"\s+", " ", text).strip()
    if text and not text.endswith("."):
        text += "."
    return text


def fallback_page_candidate(layout_text: str) -> str:
    flat = clean_spacing(layout_text)
    match = re.search(r"\bMISSED\s+APPROACH\b\s*:?.{0,900}", flat, flags=re.IGNORECASE)
    return trim_to_missed_approach_instruction(match.group(0)) if match else ""


def expanded_bounds(bbox: dict[str, Any], page_width: float, page_height: float, x_pad: float, y_pad: float) -> tuple[float, float, float, float]:
    x_center = float(bbox["x_center"])
    y_center = float(bbox["y_center"])
    width = float(bbox["width"])
    height = float(bbox["height"])
    x_min = max(0.0, x_center - width / 2.0 - x_pad) * page_width
    x_max = min(1.0, x_center + width / 2.0 + x_pad) * page_width
    y_min = max(0.0, y_center - height / 2.0 - y_pad) * page_height
    y_max = min(1.0, y_center + height / 2.0 + y_pad) * page_height
    return x_min, y_min, x_max, y_max


def extract_from_ma_bbox(
    *,
    bbox_path: Path,
    layout_path: Path,
    region: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    page_width, page_height, words = parse_bbox_words(bbox_path)
    diagnostics: dict[str, Any] = {
        "page_width": page_width,
        "page_height": page_height,
        "bbox_word_count": len(words),
        "source": "pdf_text_bbox",
        "fallback_used": False,
    }
    if region and page_width and page_height:
        attempts = [(0.04, 0.025), (0.07, 0.04), (0.10, 0.06)]
        for x_pad, y_pad in attempts:
            bounds = expanded_bounds(region["bbox"], page_width, page_height, x_pad, y_pad)
            selected = [
                word for word in words if bounds[0] <= word.x_mid <= bounds[2] and bounds[1] <= word.y_mid <= bounds[3]
            ]
            raw = words_to_lines(selected)
            candidate = trim_to_missed_approach_instruction(raw)
            diagnostics["last_bbox_bounds_points"] = bounds
            diagnostics["last_bbox_padding"] = {"x_pad": x_pad, "y_pad": y_pad}
            diagnostics["last_bbox_selected_word_count"] = len(selected)
            if re.search(r"\bMISSED\s+APPROACH\b", candidate, flags=re.IGNORECASE) and len(candidate.split()) >= 5:
                diagnostics["source"] = "pdf_text_bbox_admin_ma_region"
                diagnostics["bbox_padding"] = {"x_pad": x_pad, "y_pad": y_pad}
                diagnostics["bbox_selected_word_count"] = len(selected)
                return candidate, diagnostics
    layout_text = layout_path.read_text(encoding="utf-8", errors="replace") if layout_path.exists() else ""
    diagnostics["fallback_used"] = True
    candidate = fallback_page_candidate(layout_text)
    diagnostics["source"] = "pdf_text_layout_fallback"
    return candidate, diagnostics


def region_by_chart(regions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_chart: dict[str, dict[str, Any]] = {}
    for region in regions:
        if region.get("region_type") != "MISSED_APPROACH_TEXT":
            continue
        if not isinstance(region.get("bbox"), dict):
            continue
        chart_id = region.get("chart_id")
        if chart_id and chart_id not in by_chart:
            by_chart[chart_id] = region
    return by_chart


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dev50 gold MA prose candidates from FAA PDF text layer.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--dev50-manifest", type=Path, default=DEFAULT_DEV50_MANIFEST)
    parser.add_argument("--sanitized-regions", type=Path, default=DEFAULT_SANITIZED_REGIONS)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    dev_rows = read_jsonl(args.dev50_manifest)[: args.limit]
    ma_regions = region_by_chart(read_jsonl(args.sanitized_regions))
    pdf_dir = args.run_dir / "source_pdfs"
    text_dir = args.run_dir / "source_pdf_text"

    gold_rows: list[dict[str, Any]] = []
    extraction_rows: list[dict[str, Any]] = []
    for row in dev_rows:
        chart_id = row["chart_id"]
        pdf_path = pdf_dir / f"{chart_id}.pdf"
        bbox_path = text_dir / f"{chart_id}_bbox.html"
        layout_path = text_dir / f"{chart_id}.txt"
        download_ok, download_error = download_pdf(row["pdf_url"], pdf_path)
        pdftotext_ok = False
        pdftotext_error = None
        if download_ok:
            pdftotext_ok, pdftotext_error = run_pdftotext(pdf_path, bbox_path, layout_path)
        candidate = ""
        diagnostics: dict[str, Any] = {}
        if pdftotext_ok:
            candidate, diagnostics = extract_from_ma_bbox(
                bbox_path=bbox_path,
                layout_path=layout_path,
                region=ma_regions.get(chart_id),
            )
        status = "candidate_pdf_bbox_needs_review" if candidate else "blocked_no_candidate"
        gold_rows.append(
            {
                "chart_id": chart_id,
                "gold_ma_prose": candidate,
                "review_status": status,
                "source": diagnostics.get("source") or "pdf_text_layer",
                "checked_scopes": ["MISSED_APPROACH_TEXT"],
                "reviewer": "codex_20260503_pdf_text_bbox_candidate",
                "notes": (
                    "Candidate for dev50 runnable check only. Uses FAA PDF text layer plus sanitized admin MA_TEXT bbox; "
                    "does not use answer-side review structures, procedure database records, or method outputs."
                ),
            }
        )
        extraction_rows.append(
            {
                "chart_id": chart_id,
                "chart_name": row.get("chart_name"),
                "pdf_url": row.get("pdf_url"),
                "pdf_path": rel(pdf_path),
                "pdf_sha256": sha256_file(pdf_path),
                "bbox_text_path": rel(bbox_path),
                "layout_text_path": rel(layout_path),
                "download_ok": download_ok,
                "download_error": download_error,
                "pdftotext_ok": pdftotext_ok,
                "pdftotext_error": pdftotext_error,
                "ma_region_found": chart_id in ma_regions,
                "candidate": candidate,
                "candidate_word_count": len(candidate.split()),
                "review_status": status,
                "diagnostics": diagnostics,
            }
        )
        print(f"{chart_id}: {status}", flush=True)

    complete_count = sum(1 for row in gold_rows if row["gold_ma_prose"])
    fallback_count = sum(1 for row in extraction_rows if row.get("diagnostics", {}).get("fallback_used"))
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "dev50_rows": len(dev_rows),
        "candidate_complete_count": complete_count,
        "candidate_missing_count": len(dev_rows) - complete_count,
        "pdf_download_ok_count": sum(1 for row in extraction_rows if row["download_ok"]),
        "pdftotext_ok_count": sum(1 for row in extraction_rows if row["pdftotext_ok"]),
        "ma_region_found_count": sum(1 for row in extraction_rows if row["ma_region_found"]),
        "layout_fallback_count": fallback_count,
        "gold_ma_candidate_path": rel(args.run_dir / "inputs" / "gold_ma_text_dev50_candidate.jsonl"),
        "status": "complete_candidates_need_review" if complete_count == len(dev_rows) else "incomplete_candidates",
        "leakage_policy": {
            "uses_admin_regions": "sanitized_bbox_only",
            "uses_answer_side_review_structures": False,
            "uses_procedure_database_records": False,
            "uses_method_outputs": False,
        },
    }

    write_jsonl(args.run_dir / "inputs" / "gold_ma_text_dev50_candidate.jsonl", gold_rows)
    write_jsonl(args.run_dir / "reports" / "gold_ma_pdf_bbox_extract_candidates_dev50.jsonl", extraction_rows)
    write_json(args.run_dir / "reports" / "gold_ma_pdf_bbox_extract_candidates_dev50.json", extraction_rows)
    write_json(args.run_dir / "reports" / "dev50_gold_ma_prose_candidate_summary.json", summary)

    report_zh = [
        "# 实验组5 dev50 gold_ma_prose 候选生成报告",
        "",
        f"- 生成时间 UTC: `{summary['created_at_utc']}`",
        f"- dev50 rows: {summary['dev50_rows']}",
        f"- PDF 下载成功: {summary['pdf_download_ok_count']}/{summary['dev50_rows']}",
        f"- pdftotext 成功: {summary['pdftotext_ok_count']}/{summary['dev50_rows']}",
        f"- 找到 admin MA_TEXT bbox: {summary['ma_region_found_count']}/{summary['dev50_rows']}",
        f"- 生成 MA prose 候选: {summary['candidate_complete_count']}/{summary['dev50_rows']}",
        f"- layout fallback 次数: {summary['layout_fallback_count']}",
        f"- 状态: `{summary['status']}`",
        "",
        "## 重要限制",
        "",
        "- 这是 dev50 跑通用候选，不是正式人工 adjudicated gold。",
        "- 候选只使用 FAA PDF text layer 和去泄漏 admin MA_TEXT 区域框。",
        "- 没有使用 field review、canonical answer、score、CIFP/ARINC 424 或任何方法输出。",
        "",
        "## 输出",
        "",
        f"- candidate jsonl: `{summary['gold_ma_candidate_path']}`",
        "- extraction details: `formal_runs/experiment5/experiment5_dev50_20260503_r1/reports/gold_ma_pdf_bbox_extract_candidates_dev50.jsonl`",
        "",
        "## 下一步",
        "",
        "1. 先用这个 candidate 文件跑 A3/B2 的 dev50 pipeline check。",
        "2. 如果要把 dev50 结果作为正式诊断数字，需人工抽查并改成 adjudicated gold。",
    ]
    write_text(args.run_dir / "reports" / "dev50_gold_ma_prose_candidate_report_zh.md", "\n".join(report_zh) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if complete_count == len(dev_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
