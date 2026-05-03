from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "formal_runs" / "experiment5" / "experiment5_dev50_20260503_r1"
DEFAULT_ADMIN_EXPORT = (
    REPO_ROOT
    / "formal_runs"
    / "experiment5"
    / "admin_exports"
    / "shujuji_annotation_export_2026-05-03T08-34-13-795Z.json"
)
DEFAULT_DEV50_MANIFEST = DEFAULT_RUN_DIR / "manifests" / "dev50_chart_manifest.jsonl"
SCHEMA_PATH = REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"

ANSWER_SIDE_KEYS = {
    "canonical_answer",
    "canonical_leg_index",
    "leg_type",
    "Q_terminator",
    "target",
    "score",
    "field_review_v2",
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


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


def latest_submissions_by_chart(admin_export: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    export = json.loads(admin_export.read_text(encoding="utf-8"))
    submissions = export.get("datasets", {}).get("formal300", {}).get("annotations", {}).get("submissions", [])
    latest: dict[str, dict[str, Any]] = {}
    duplicate_counts: Counter[str] = Counter()
    for submission in submissions:
        data = submission.get("data") or {}
        chart_id = data.get("chart_id")
        if not chart_id:
            continue
        duplicate_counts[chart_id] += 1
        current = latest.get(chart_id)
        saved_at = str(data.get("saved_at") or "")
        current_saved_at = str((current or {}).get("data", {}).get("saved_at") or "")
        if current is None or saved_at >= current_saved_at:
            latest[chart_id] = submission
    return latest, {
        "admin_export_path": rel(admin_export),
        "admin_export_sha256": sha256_file(admin_export),
        "exported_at": export.get("exported_at"),
        "submission_rows": len(submissions),
        "unique_chart_submissions": len(latest),
        "charts_with_multiple_submissions": sum(1 for count in duplicate_counts.values() if count > 1),
    }


def sanitized_region(region: dict[str, Any], chart_id: str, index: int) -> dict[str, Any]:
    keep_keys = [
        "final_region_id",
        "source_region_id",
        "region_type",
        "bbox",
        "label",
        "ocr_text",
        "annotation_scope",
        "element_role",
        "step_id",
        "parent_step_region_id",
        "is_formal_annotation_candidate",
        "notes",
        "review_action",
        "needs_discussion",
    ]
    row = {key: region.get(key) for key in keep_keys if key in region}
    row["chart_id"] = chart_id
    row["region_index"] = index
    return row


def parse_region_facts(region: dict[str, Any]) -> list[dict[str, Any]]:
    chart_id = region["chart_id"]
    region_id = region.get("final_region_id") or region.get("source_region_id")
    region_type = region.get("region_type")
    label = str(region.get("label") or "")
    base = {
        "chart_id": chart_id,
        "evidence_region_id": region_id,
        "region_type": region_type,
        "bbox": region.get("bbox"),
        "review_action": region.get("review_action"),
        "annotation_scope": region.get("annotation_scope"),
        "label": label,
    }
    facts: list[dict[str, Any]] = []

    def add(fact_type: str, value: Any, status: str = "observed") -> None:
        facts.append({**base, "fact_type": fact_type, "status": status, "value": value})

    if region_type == "MISSED_APPROACH_TEXT":
        add("ma_text_region_present", {"region_id": region_id})
        return facts
    if region_type == "PLAN_VIEW":
        add("plan_view_region_present", {"region_id": region_id})
        return facts
    if region_type == "MISSED_APPROACH_DETAIL_AREA":
        add("ma_detail_region_present", {"region_id": region_id})
        return facts
    if region_type == "CLIMB_ARROW":
        add("climb_arrow_visible", True)
        return facts
    if region_type == "FIX_SYMBOL":
        add("fix_symbol_visible", True)
        return facts
    if region_type == "PATH_SEGMENT":
        add("path_segment_visible", True)
        return facts

    for match in re.finditer(r"FIX_TEXT:\s*([A-Z0-9]+)\s*->\s*([A-Z0-9]+)", label):
        add("fix_text_visible", {"raw_text": match.group(1), "fix_ident": match.group(2)})

    for match in re.finditer(r"ALTITUDE_TEXT:\s*([0-9]{2,5})\s*->\s*AT_OR_ABOVE\s*([0-9]{2,5})\s*ft", label):
        add(
            "altitude_text_visible",
            {"raw_text": match.group(1), "constraint": "AT_OR_ABOVE", "altitude_ft": int(match.group(2))},
        )

    for match in re.finditer(r"HEADING_TEXT:\s*(.*?)\s*->\s*type=course_deg,\s*course_deg=([0-9.]+)", label):
        add("heading_text_visible", {"raw_text": match.group(1).strip(), "course_deg": float(match.group(2))})

    radial_pattern = re.compile(
        r"(?:RADIAL_TEXT|NAVAID_TEXT|OUTBOUND_INBOUND_MARK):\s*(.*?)\s*->\s*"
        r"type=navaid_radial,\s*navaid=([A-Z0-9]+),\s*radial_deg=([0-9.]+),\s*direction=([a-zA-Z_]+)"
    )
    for match in radial_pattern.finditer(label):
        add(
            "navaid_radial_text_visible",
            {
                "raw_text": match.group(1).strip(),
                "navaid": match.group(2),
                "radial_deg": float(match.group(3)),
                "direction": match.group(4),
            },
        )

    if not facts and region_type in {"ALTITUDE_TEXT", "FIX_TEXT", "HEADING_TEXT", "RADIAL_TEXT", "NAVAID_TEXT"}:
        add("unparsed_text_annotation_visible", {"raw_label": label}, status="observed_unparsed")
    return facts


def build_observable_rows(
    chart_ids: list[str],
    regions_by_chart: dict[str, list[dict[str, Any]]],
    *,
    allowed_review_actions: set[str],
    source_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    facts_flat: list[dict[str, Any]] = []
    for chart_id in chart_ids:
        chart_regions = [
            region for region in regions_by_chart.get(chart_id, []) if region.get("review_action") in allowed_review_actions
        ]
        facts: list[dict[str, Any]] = []
        for region in chart_regions:
            facts.extend(parse_region_facts(region))
        row = {
            "schema_version": "experiment5_gold_observable_admin_regions_v2",
            "chart_id": chart_id,
            "review_status": f"{source_name}_extracted",
            "source": "admin_region_annotations_sanitized",
            "allowed_review_actions": sorted(allowed_review_actions),
            "checked_scopes": ["MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"],
            "evidence_region_ids": [
                region.get("final_region_id") or region.get("source_region_id") for region in chart_regions
            ],
            "observable_facts": facts,
            "notes": "Method-safe observable input: no canonical_answer, no canonical_leg_index, no leg_type.",
        }
        rows.append(row)
        facts_flat.extend({**fact, "observable_source": source_name} for fact in facts)
    return rows, facts_flat


def scan_key_names(value: Any, forbidden: set[str]) -> dict[str, Any]:
    hits: list[dict[str, str]] = []

    def visit(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key in forbidden:
                    hits.append({"path": path or "$", "key": key})
                visit(item, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                visit(item, f"{path}[{index}]")

    visit(value, "")
    return {"hit_count": len(hits), "hits": hits[:50], "truncated": len(hits) > 50}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export dev50 admin artifacts into answer, review, evidence, and method-safe input files.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--admin-export", type=Path, default=DEFAULT_ADMIN_EXPORT)
    parser.add_argument("--dev50-manifest", type=Path, default=DEFAULT_DEV50_MANIFEST)
    args = parser.parse_args()

    chart_ids = [row["chart_id"] for row in read_jsonl(args.dev50_manifest)]
    latest, export_meta = latest_submissions_by_chart(args.admin_export)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    gold_answer_rows: list[dict[str, Any]] = []
    field_review_rows: list[dict[str, Any]] = []
    evidence_link_rows: list[dict[str, Any]] = []
    region_rows: list[dict[str, Any]] = []
    regions_by_chart: dict[str, list[dict[str, Any]]] = defaultdict(list)
    schema_errors: dict[str, list[str]] = {}
    missing: list[str] = []

    for chart_id in chart_ids:
        submission = latest.get(chart_id)
        if submission is None:
            missing.append(chart_id)
            continue
        data = submission.get("data") or {}
        answer = data.get("annotation_pr28_json")
        errors = []
        if isinstance(answer, dict):
            errors = [
                (".".join(str(part) for part in err.path) or "$") + f": {err.message}"
                for err in sorted(validator.iter_errors(answer), key=lambda err: list(err.path))
            ]
        else:
            errors = ["annotation_pr28_json missing or not object"]
        if errors:
            schema_errors[chart_id] = errors
        gold_answer_rows.append(
            {
                "chart_id": chart_id,
                "source": "admin_annotation_pr28_json",
                "review_status": data.get("review_status"),
                "saved_at": data.get("saved_at"),
                "saved_by": data.get("saved_by"),
                "annotation_pr28_json": answer,
                "schema_validation_errors": errors,
            }
        )

        for index, region in enumerate(data.get("regions") or [], start=1):
            clean = sanitized_region(region, chart_id, index)
            region_rows.append(clean)
            regions_by_chart[chart_id].append(clean)

        for index, review in enumerate(data.get("field_reviews") or [], start=1):
            row = dict(review)
            row["review_index"] = index
            field_review_rows.append(row)
            evidence_link_rows.append(
                {
                    "chart_id": chart_id,
                    "field_key": review.get("field_key"),
                    "candidate_leg_id": review.get("candidate_leg_id"),
                    "canonical_leg_index": review.get("canonical_leg_index"),
                    "leg_type": review.get("leg_type"),
                    "field_name": review.get("field_name"),
                    "support_mode": review.get("support_mode"),
                    "review_status": review.get("review_status"),
                    "evidence_region_ids": review.get("evidence_region_ids") or [],
                    "required_evidence_region_ids": review.get("required_evidence_region_ids") or [],
                    "secondary_evidence_region_ids": review.get("secondary_evidence_region_ids") or [],
                    "canonical_answer": review.get("canonical_answer"),
                    "checked_scopes": review.get("checked_scopes") or [],
                    "checked_sources": review.get("checked_sources") or [],
                }
            )

    observable_accept, facts_accept = build_observable_rows(
        chart_ids,
        regions_by_chart,
        allowed_review_actions={"accept"},
        source_name="accept_only",
    )
    observable_all, facts_all = build_observable_rows(
        chart_ids,
        regions_by_chart,
        allowed_review_actions={"accept", "pending"},
        source_name="accept_pending",
    )

    output_dir = args.run_dir / "admin_artifacts"
    write_jsonl(output_dir / "admin_gold_answer_dev50.jsonl", gold_answer_rows)
    write_jsonl(output_dir / "admin_field_review_dev50.jsonl", field_review_rows)
    write_jsonl(output_dir / "admin_regions_dev50.jsonl", region_rows)
    write_jsonl(output_dir / "admin_evidence_links_dev50.jsonl", evidence_link_rows)
    write_jsonl(args.run_dir / "inputs" / "gold_observable_dev50_accept.jsonl", observable_accept)
    write_jsonl(args.run_dir / "inputs" / "gold_observable_dev50_accept_pending.jsonl", observable_all)
    write_jsonl(args.run_dir / "reports" / "gold_observable_dev50_accept_facts.jsonl", facts_accept)
    write_jsonl(args.run_dir / "reports" / "gold_observable_dev50_accept_pending_facts.jsonl", facts_all)

    region_counter = Counter(row.get("region_type") for row in region_rows)
    review_action_counter = Counter(row.get("review_action") for row in region_rows)
    support_mode_counter = Counter(row.get("support_mode") for row in field_review_rows)
    field_name_counter = Counter(row.get("field_name") for row in field_review_rows)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "export_meta": export_meta,
        "dev50_chart_count": len(chart_ids),
        "missing_submission_chart_ids": missing,
        "gold_answer_rows": len(gold_answer_rows),
        "gold_answer_schema_error_chart_count": len(schema_errors),
        "gold_answer_schema_errors": schema_errors,
        "field_review_rows": len(field_review_rows),
        "region_rows": len(region_rows),
        "evidence_link_rows": len(evidence_link_rows),
        "region_type_counts": dict(sorted(region_counter.items())),
        "region_review_action_counts": dict(sorted(review_action_counter.items())),
        "field_review_support_mode_counts": dict(sorted(support_mode_counter.items())),
        "field_review_field_name_counts": dict(sorted(field_name_counter.items())),
        "observable_accept_rows": len(observable_accept),
        "observable_accept_fact_rows": len(facts_accept),
        "observable_accept_pending_rows": len(observable_all),
        "observable_accept_pending_fact_rows": len(facts_all),
        "method_safe_accept_scan": scan_key_names(observable_accept, ANSWER_SIDE_KEYS),
        "method_safe_accept_pending_scan": scan_key_names(observable_all, ANSWER_SIDE_KEYS),
        "outputs": {
            "admin_gold_answer": rel(output_dir / "admin_gold_answer_dev50.jsonl"),
            "admin_field_review": rel(output_dir / "admin_field_review_dev50.jsonl"),
            "admin_regions": rel(output_dir / "admin_regions_dev50.jsonl"),
            "admin_evidence_links": rel(output_dir / "admin_evidence_links_dev50.jsonl"),
            "gold_observable_accept": rel(args.run_dir / "inputs" / "gold_observable_dev50_accept.jsonl"),
            "gold_observable_accept_pending": rel(args.run_dir / "inputs" / "gold_observable_dev50_accept_pending.jsonl"),
        },
    }
    write_json(args.run_dir / "reports" / "admin_dev50_artifacts_summary.json", summary)

    report = [
        "# 实验组5 dev50 后台审核工件导出报告",
        "",
        f"- 生成时间 UTC: `{summary['created_at_utc']}`",
        f"- dev50 charts: {summary['dev50_chart_count']}",
        f"- gold answers: {summary['gold_answer_rows']}",
        f"- gold answer schema error charts: {summary['gold_answer_schema_error_chart_count']}",
        f"- field reviews: {summary['field_review_rows']}",
        f"- regions: {summary['region_rows']}",
        f"- evidence links: {summary['evidence_link_rows']}",
        f"- observable accept facts: {summary['observable_accept_fact_rows']}",
        f"- observable accept+pending facts: {summary['observable_accept_pending_fact_rows']}",
        f"- method-safe accept forbidden key hits: {summary['method_safe_accept_scan']['hit_count']}",
        f"- method-safe accept+pending forbidden key hits: {summary['method_safe_accept_pending_scan']['hit_count']}",
        "",
        "## 输出文件",
        "",
    ]
    for name, path in summary["outputs"].items():
        report.append(f"- `{name}`: `{path}`")
    report.extend(
        [
            "",
            "## 用法",
            "",
            "- `admin_gold_answer_dev50.jsonl` 是最终人工答案，只用于评分或审计。",
            "- `admin_field_review_dev50.jsonl` 和 `admin_evidence_links_dev50.jsonl` 是完整审核关系，用于 oracle 诊断和错误归因。",
            "- `gold_observable_dev50_accept*.jsonl` 是去答案字段后的方法输入，可给 G 系列使用。",
        ]
    )
    write_text(args.run_dir / "reports" / "admin_dev50_artifacts_export_report_zh.md", "\n".join(report) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not missing and not schema_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
