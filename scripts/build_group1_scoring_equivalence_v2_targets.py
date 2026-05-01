from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
)

TARGET_DIR = REPO_ROOT / "benchmark_exports" / "derived" / "v2" / "formal300" / "targets"
COMBINED_TARGET_PATH = TARGET_DIR / "canonical_proxy_gt_combined.json"
FIELD_TARGETS_PATH = TARGET_DIR / "field_targets.jsonl"
EVIDENCE_PROVENANCE_PATH = TARGET_DIR / "evidence_provenance.jsonl"
SCHEMA_PATH = REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"

OUT_TARGET_DIR = ARTIFACT_ROOT
OUT_REPORT_DIR = ARTIFACT_ROOT
OUT_MANIFEST_DIR = ARTIFACT_ROOT

DEGREE_KEYS = {"course_deg", "radial_deg", "inbound_course_deg"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
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
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def round_display_degree(value: float) -> int:
    # Aviation chart degrees are normally displayed as nearest integer degrees.
    # Use half-up rounding rather than Python bankers' rounding.
    rounded = int(math.floor(float(value) + 0.5))
    if rounded == 0 and value > 359.5:
        return 360
    return rounded


def decimal_degree_risk(value: Any) -> bool:
    if not is_number(value):
        return False
    return abs(float(value) - round_display_degree(float(value))) > 1e-9


def normalize_degree_fields(value: Any) -> tuple[Any, list[dict[str, Any]]]:
    """Return chart-display value and degree changes for a canonical answer value."""
    changed = copy.deepcopy(value)
    changes: list[dict[str, Any]] = []

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, child in list(obj.items()):
                child_path = f"{path}.{key}" if path else key
                if key in DEGREE_KEYS and is_number(child):
                    rounded = round_display_degree(float(child))
                    if child != rounded:
                        obj[key] = rounded
                        changes.append(
                            {
                                "subfield_path": child_path,
                                "raw_value": child,
                                "chart_display_value": rounded,
                                "reason": "degree_display_rounding",
                            }
                        )
                else:
                    walk(child, child_path)
        elif isinstance(obj, list):
            for idx, child in enumerate(obj):
                walk(child, f"{path}[{idx}]")

    walk(changed, "")
    return changed, changes


def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    question = row.get("question_field")
    target = row.get("target")
    target_value = target.get("value") if isinstance(target, dict) else None
    status = target.get("status") if isinstance(target, dict) else None

    policy = "exact_status_value"
    field_category = "other"
    risk_types: list[str] = []
    manual_review_required = False
    notes: list[str] = []
    chart_display_target = copy.deepcopy(target)
    subfield_policies: dict[str, str] = {}

    if question == "leg_count":
        policy = "exact_status_value"
        field_category = "strict"

    elif question == "Q_terminator":
        policy = "exact_status_value"
        field_category = "strict"

    elif question == "Q1_fix_ident":
        policy = "normalized_string"
        field_category = "fix_navaid"
        if status == "present":
            risk_types.append("fix_navaid_format_normalization")
            notes.append("Allow conservative ident normalization only; no fuzzy fix matching.")

    elif question == "Q2_altitude_constraint":
        policy = "exact_status_value"
        field_category = "strict"

    elif question == "Q3_turn":
        policy = "exact_status_value"
        field_category = "strict"

    elif question == "Q4_course_or_radial":
        field_category = "course_radial"
        if status == "present" and isinstance(target_value, dict):
            value_type = target_value.get("type")
            if value_type == "direct":
                policy = "exact_status_value"
                notes.append("Direct-to-fix course/radial answer has no numeric degree to round.")
            elif any(key in target_value for key in DEGREE_KEYS):
                policy = "degree_display_rounding"
                risk_types.append("degree_decimal_display_rounding")
                for key in DEGREE_KEYS:
                    if key in target_value:
                        subfield_policies[key] = "degree_display_rounding"
                new_value, degree_changes = normalize_degree_fields(target_value)
                if degree_changes:
                    chart_display_target = {"status": status, "value": new_value}
                notes.append("Degree fields use chart-display integer rounding; reciprocal matching is not automatic.")
            else:
                policy = "manual_review_required"
                manual_review_required = True
                risk_types.append("unknown_course_radial_shape")
                notes.append("Present Q4 value lacks recognized type/direct/degree fields.")
        elif status == "present":
            policy = "manual_review_required"
            manual_review_required = True
            risk_types.append("unknown_course_radial_shape")

    elif question == "Q5_hold_params":
        field_category = "course_radial"
        if status == "present" and isinstance(target_value, dict):
            policy = "degree_display_rounding"
            new_value, degree_changes = normalize_degree_fields(target_value)
            if degree_changes:
                chart_display_target = {"status": status, "value": new_value}
                risk_types.append("degree_decimal_display_rounding")
            if "inbound_course_deg" in target_value:
                subfield_policies["inbound_course_deg"] = "degree_display_rounding"
            if degree_changes:
                notes.append("Only the hold inbound course degree is rounded for chart-display equivalence; other hold fields remain strict.")
            else:
                policy = "exact_status_value"
        elif status == "present":
            policy = "manual_review_required"
            manual_review_required = True
            risk_types.append("unknown_hold_params_shape")

    else:
        manual_review_required = True
        policy = "manual_review_required"
        risk_types.append("unknown_question_field")

    return {
        "sample_id": row.get("sample_id"),
        "chart_id": row.get("chart_id"),
        "field_path": row.get("field_path"),
        "leg_index": row.get("leg_index"),
        "question_field": question,
        "field_category": field_category,
        "raw_424_target": target,
        "chart_display_target": chart_display_target,
        "comparison_policy": policy,
        "subfield_policies": subfield_policies,
        "risk_types": risk_types,
        "manual_review_required": manual_review_required,
        "notes": notes,
    }


def apply_target_to_combined(combined: dict[str, Any], row: dict[str, Any], target: dict[str, Any]) -> None:
    chart = combined[row["chart_id"]]
    missed = chart["missed_approach"]
    question = row["question_field"]
    if question == "leg_count":
        missed["leg_count"] = target
        return
    leg_index = row["leg_index"]
    for leg in missed.get("legs", []):
        if leg.get("leg_index") == leg_index:
            leg.setdefault("answers", {})[question] = target
            return
    raise KeyError(f"Cannot find leg_index={leg_index} for {row['chart_id']} {question}")


def validate_combined_targets(combined: dict[str, Any]) -> dict[str, Any]:
    schema = read_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    invalid = []
    for chart_id, obj in combined.items():
        errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
        if errors:
            invalid.append(
                {
                    "chart_id": chart_id,
                    "errors": [
                        {
                            "path": ".".join(str(part) for part in err.path) or "$",
                            "message": err.message,
                        }
                        for err in errors
                    ],
                }
            )
    return {"schema_valid_count": len(combined) - len(invalid), "schema_invalid_count": len(invalid), "invalid": invalid}


def main() -> int:
    OUT_TARGET_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    combined_v1 = read_json(COMBINED_TARGET_PATH)
    field_rows = read_jsonl(FIELD_TARGETS_PATH)
    combined_v2 = copy.deepcopy(combined_v1)

    policy_rows: list[dict[str, Any]] = []
    field_targets_v2: list[dict[str, Any]] = []
    risk_rows: list[dict[str, Any]] = []
    diff_rows: list[dict[str, Any]] = []
    manual_review_rows: list[dict[str, Any]] = []

    for row in field_rows:
        policy = classify_row(row)
        policy_rows.append(policy)

        new_row = copy.deepcopy(row)
        new_row["target"] = policy["chart_display_target"]
        field_targets_v2.append(new_row)
        apply_target_to_combined(combined_v2, row, policy["chart_display_target"])

        if policy["risk_types"]:
            risk_rows.append(
                {
                    "sample_id": row.get("sample_id"),
                    "chart_id": row.get("chart_id"),
                    "field_path": row.get("field_path"),
                    "leg_index": row.get("leg_index"),
                    "question_field": row.get("question_field"),
                    "field_category": policy["field_category"],
                    "risk_types": policy["risk_types"],
                    "recommended_policy": policy["comparison_policy"],
                    "raw_424_target": policy["raw_424_target"],
                    "chart_display_target": policy["chart_display_target"],
                    "manual_review_required": policy["manual_review_required"],
                    "notes": policy["notes"],
                }
            )
        if policy["manual_review_required"]:
            manual_review_rows.append(policy)
        if policy["raw_424_target"] != policy["chart_display_target"]:
            diff_rows.append(
                {
                    "sample_id": row.get("sample_id"),
                    "chart_id": row.get("chart_id"),
                    "field_path": row.get("field_path"),
                    "leg_index": row.get("leg_index"),
                    "question_field": row.get("question_field"),
                    "field_category": policy["field_category"],
                    "comparison_policy": policy["comparison_policy"],
                    "raw_424_target": policy["raw_424_target"],
                    "chart_display_target": policy["chart_display_target"],
                    "risk_types": policy["risk_types"],
                    "notes": policy["notes"],
                }
            )

    validation = validate_combined_targets(combined_v2)

    write_json(OUT_TARGET_DIR / "canonical_proxy_gt_chart_display_v2.json", combined_v2)
    write_jsonl(OUT_TARGET_DIR / "field_targets_chart_display_v2.jsonl", field_targets_v2)
    write_jsonl(OUT_TARGET_DIR / "comparison_policy_v2.jsonl", policy_rows)
    write_jsonl(OUT_TARGET_DIR / "risk_field_inventory.jsonl", risk_rows)
    write_jsonl(OUT_TARGET_DIR / "target_v1_to_v2_diff.jsonl", diff_rows)
    write_jsonl(OUT_TARGET_DIR / "manual_review_required_fields.jsonl", manual_review_rows)

    policy_counter = Counter(row["comparison_policy"] for row in policy_rows)
    category_counter = Counter(row["field_category"] for row in policy_rows)
    risk_counter = Counter(risk for row in risk_rows for risk in row["risk_types"])
    question_counter = Counter(row.get("question_field") for row in field_rows)
    diff_by_question = Counter(row["question_field"] for row in diff_rows)
    manual_by_question = Counter(row["question_field"] for row in manual_review_rows)

    output_paths = [
        OUT_TARGET_DIR / "canonical_proxy_gt_chart_display_v2.json",
        OUT_TARGET_DIR / "field_targets_chart_display_v2.jsonl",
        OUT_TARGET_DIR / "comparison_policy_v2.jsonl",
        OUT_TARGET_DIR / "risk_field_inventory.jsonl",
        OUT_TARGET_DIR / "target_v1_to_v2_diff.jsonl",
        OUT_TARGET_DIR / "manual_review_required_fields.jsonl",
    ]
    manifest = {
        "run_id": "group1_scoring_equivalence_v2_20260501_r1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_root": rel(ARTIFACT_ROOT),
        "source_inputs": {
            "canonical_proxy_gt_combined": {
                "path": rel(COMBINED_TARGET_PATH),
                "sha256": sha256(COMBINED_TARGET_PATH),
            },
            "field_targets": {"path": rel(FIELD_TARGETS_PATH), "sha256": sha256(FIELD_TARGETS_PATH)},
            "evidence_provenance": {
                "path": rel(EVIDENCE_PROVENANCE_PATH),
                "sha256": sha256(EVIDENCE_PROVENANCE_PATH),
            },
            "schema": {"path": rel(SCHEMA_PATH), "sha256": sha256(SCHEMA_PATH)},
        },
        "outputs": {
            path.name: {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in output_paths
        },
        "counts": {
            "charts": len(combined_v1),
            "field_rows_v1": len(field_rows),
            "field_rows_v2": len(field_targets_v2),
            "policy_rows": len(policy_rows),
            "risk_rows": len(risk_rows),
            "diff_rows": len(diff_rows),
            "manual_review_required_rows": len(manual_review_rows),
            "schema_valid_count": validation["schema_valid_count"],
            "schema_invalid_count": validation["schema_invalid_count"],
        },
        "policy_counts": dict(policy_counter),
        "field_category_counts": dict(category_counter),
        "risk_type_counts": dict(risk_counter),
        "question_field_counts": dict(question_counter),
        "diff_by_question_field": dict(diff_by_question),
        "manual_review_by_question_field": dict(manual_by_question),
        "validation": validation,
    }
    write_json(OUT_MANIFEST_DIR / "target_v2_manifest.json", manifest)
    write_json(OUT_REPORT_DIR / "target_v2_summary.json", manifest)

    summary_md = [
        "# Group 1 scoring-equivalence v2 target build summary",
        "",
        f"- Run ID: `{manifest['run_id']}`",
        f"- Charts: {len(combined_v1)}",
        f"- Field target rows: {len(field_rows)}",
        f"- Policy rows: {len(policy_rows)}",
        f"- Risk rows: {len(risk_rows)}",
        f"- v1 -> v2 changed rows: {len(diff_rows)}",
        f"- Manual review required rows: {len(manual_review_rows)}",
        f"- Schema valid charts: {validation['schema_valid_count']}",
        f"- Schema invalid charts: {validation['schema_invalid_count']}",
        "",
        "## Policy Counts",
        "",
    ]
    for key, count in sorted(policy_counter.items()):
        summary_md.append(f"- `{key}`: {count}")
    summary_md.extend(["", "## Diff By Question Field", ""])
    for key, count in sorted(diff_by_question.items()):
        summary_md.append(f"- `{key}`: {count}")
    summary_md.extend(["", "## Risk Type Counts", ""])
    for key, count in sorted(risk_counter.items()):
        summary_md.append(f"- `{key}`: {count}")
    summary_md.extend(["", "## Notes", ""])
    summary_md.append("This build does not read model predictions and does not rerun OCR/LLM/VLM methods.")
    summary_md.append("It only derives chart-display-aware targets and comparison policies from the existing formal300 target files.")
    (OUT_REPORT_DIR / "target_v2_summary.md").write_text("\n".join(summary_md) + "\n", encoding="utf-8")

    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))
    if validation["schema_invalid_count"]:
        print("Schema validation failed for target v2.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
