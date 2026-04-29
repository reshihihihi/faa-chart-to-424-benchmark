from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_pilot10_anthropic import (  # noqa: E402
    DATA_DIR,
    SCHEMA_PATH,
    read_jsonl,
    resolve_package_path,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)


DEFAULT_RUN_ID = "pilot10_group1_a1_a2_rules_ordinary_ocr_20260428_r1"
RUN_OUTPUT_ROOT = ROOT / "predictions" / "pilot10_external"
DEFAULT_OCR1_TEXT_ROOT = (
    ROOT / "ocr_artifacts" / "pilot10_external" / "ocr1_paddleocr_ppocrv5_20260428_r1" / "full_text"
)
DEFAULT_OCR2_TEXT_ROOT = (
    ROOT / "ocr_artifacts" / "pilot10_external" / "ocr2_tesseract5_20260428_r1" / "full_text"
)
RULE_SPEC = ROOT / "docs" / "group1_a1_a2_rules_candidate_v1.md"


def display_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def file_artifact(path: Path) -> dict[str, Any]:
    return {
        "path": display_path(path),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() else None,
    }


def ocr_manifest_artifacts(ocr_text_root: Path) -> dict[str, Any]:
    artifact_root = ocr_text_root.parent
    return {
        "artifact_root": display_path(artifact_root),
        "run_manifest": file_artifact(artifact_root / "run_manifest.json"),
        "manifest_jsonl": file_artifact(artifact_root / "manifest.jsonl"),
    }


def input_artifacts(rows: list[dict[str, Any]], ocr1_text_root: Path, ocr2_text_root: Path) -> list[dict[str, Any]]:
    artifacts = []
    for row in rows:
        chart_id = row["chart_id"]
        artifacts.append(
            {
                "sample_id": row["pilot_sample_id"],
                "chart_id": chart_id,
                "A1_ocr_text": file_artifact(ocr1_text_root / f"{chart_id}.txt"),
                "A2_ocr_text": file_artifact(ocr2_text_root / f"{chart_id}.txt"),
            }
        )
    return artifacts


TERMINATORS = {
    "CA",
    "CF",
    "CI",
    "CR",
    "DF",
    "FA",
    "FM",
    "HA",
    "HF",
    "HM",
    "IF",
    "RF",
    "TF",
    "VA",
    "VD",
    "VI",
    "VM",
    "VR",
    "AF",
    "CD",
    "FC",
    "FD",
    "VC",
    "PI",
}
STOPWORDS = {
    "AIRPORT",
    "APP",
    "APCH",
    "APPROACH",
    "AT",
    "CLIMB",
    "COURSE",
    "CRS",
    "DME",
    "DIRECT",
    "FIX",
    "FROM",
    "HEADING",
    "HDG",
    "HOLD",
    "HOLDING",
    "ILS",
    "LOC",
    "MISSED",
    "NAVAID",
    "NDB",
    "NM",
    "RADIAL",
    "RIGHT",
    "LEFT",
    "RNAV",
    "RNP",
    "RUNWAY",
    "THEN",
    "TO",
    "TURN",
    "VOR",
    "VORTAC",
}


def answer(status: str, value: Any = None) -> dict[str, Any]:
    if status != "present":
        value = None
    return {"status": status, "value": value}


def blank_leg(index: int) -> dict[str, Any]:
    return {
        "leg_index": index,
        "answers": {
            "Q_terminator": answer("unknown"),
            "Q1_fix_ident": answer("unknown"),
            "Q2_altitude_constraint": answer("not_applicable"),
            "Q3_turn": answer("not_applicable"),
            "Q4_course_or_radial": answer("unknown"),
            "Q5_hold_params": answer("not_applicable"),
        },
    }


def canonical_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "chart_id": row["chart_id"],
        "procedure": {
            "airport": row["airport"],
            "approach_ident": row["proc_ident"],
            "chart_name": row["chart_name"],
        },
        "missed_approach": {"leg_count": answer("unknown"), "legs": []},
    }


def normalize_text(text: str) -> str:
    text = text.upper()
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def missed_approach_window(text: str) -> tuple[str, dict[str, Any]]:
    match = re.search(r"\bMISSED\s+(?:APPROACH|APCH)\b:?", text)
    if not match:
        return "", {"found": False, "reason": "missing_missed_approach_heading"}

    start = match.start()
    search_end = min(len(text), start + 900)
    local = text[start:search_end]
    boundary = re.search(
        r"\n\s*(?:CATEGORY|CIRCLING|APT ELEV|TDZE|TCH|MIRL|REIL|HIRL|NOTE:|PROFILE|CHART)\b",
        local,
    )
    end = start + boundary.start() if boundary and boundary.start() > 80 else search_end
    return text[start:end], {"found": True, "start_char": start, "end_char": end}


def split_clauses(window: str) -> list[str]:
    body = re.sub(r"^\s*MISSED\s+(?:APPROACH|APCH)\b:?", "", window).strip()
    body = re.sub(r"\bMISSED\s+(?:APPROACH|APCH)\b:?", " ", body)
    parts = re.split(r";|\.|\bTHEN\b|,\s*THEN\b", body)
    clauses = []
    for part in parts:
        clause = re.sub(r"\s+", " ", part).strip(" ,:-")
        if not clause:
            continue
        if re.search(r"\b(CLIMB|DIRECT|HOLD|HOLDING|HEADING|HDG|COURSE|CRS|RADIAL|R-\d{3})\b", clause):
            clauses.append(clause)
    return clauses[:12]


def first_altitude(clause: str) -> int | None:
    for pattern in [
        r"\bCLIMB(?:ING)?(?:\s+\w+){0,4}\s+TO\s+(\d{3,5})\b",
        r"\bTO\s+(\d{3,5})\b",
        r"\bAT\s+(\d{3,5})\b",
    ]:
        match = re.search(pattern, clause)
        if match:
            value = int(match.group(1))
            if 200 <= value <= 20000:
                return value
    return None


def clean_ident(value: str | None) -> str | None:
    if not value:
        return None
    ident = re.sub(r"[^A-Z0-9]", "", value.upper())
    if not (1 <= len(ident) <= 5):
        return None
    if ident in STOPWORDS:
        return None
    if ident.isdigit():
        return None
    return ident


def schema_degree(value: str | int | float) -> float | None:
    try:
        degree = float(value)
    except (TypeError, ValueError):
        return None
    if degree == 360.0:
        return 359.9
    if 0.0 <= degree <= 359.9:
        return degree
    return None


def direct_ident(clause: str) -> str | None:
    match = re.search(r"\bDIRECT\s+([A-Z0-9]{2,5})\b", clause)
    return clean_ident(match.group(1) if match else None)


def hold_ident(clause: str) -> str | None:
    for pattern in [
        r"\bHOLD(?:ING)?\s+(?:AT|ON)\s+([A-Z0-9]{2,5})\b",
        r"\bTO\s+([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b",
        r"\b([A-Z0-9]{2,5})\s+(?:AND\s+)?HOLD\b",
    ]:
        match = re.search(pattern, clause)
        ident = clean_ident(match.group(1) if match else None)
        if ident:
            return ident
    return None


def to_ident(clause: str) -> str | None:
    for match in re.finditer(r"\bTO\s+([A-Z0-9]{2,5})\b", clause):
        ident = clean_ident(match.group(1))
        if ident:
            return ident
    return None


def navaid_radial(clause: str) -> dict[str, Any] | None:
    match = re.search(
        r"\b([A-Z0-9]{2,5})\s+(?:VOR|VORTAC|NDB|DME)?\s*R-?\s*([0-3]\d{2})\b(?:\s*(OUTBOUND|INBOUND))?",
        clause,
    )
    if not match:
        match = re.search(r"\b([A-Z0-9]{2,5})\s+RADIAL\s+([0-3]\d{2})\b(?:\s*(OUTBOUND|INBOUND))?", clause)
    if not match:
        return None
    navaid = clean_ident(match.group(1))
    if not navaid:
        return None
    radial_deg = schema_degree(match.group(2))
    if radial_deg is None:
        return None
    direction = (match.group(3) or "").lower()
    if direction not in {"outbound", "inbound"}:
        direction = "outbound"
    return {
        "type": "navaid_radial",
        "navaid": navaid,
        "radial_deg": radial_deg,
        "direction": direction,
    }


def course_value(clause: str) -> dict[str, Any] | None:
    match = re.search(r"\b(?:HEADING|HDG|COURSE|CRS)\s+([0-3]\d{2})\b", clause)
    if not match:
        return None
    degree = schema_degree(match.group(1))
    if degree is None:
        return None
    return {"type": "course_deg", "course_deg": degree}


def hold_params(clause: str) -> dict[str, Any]:
    inbound = None
    match = re.search(r"\b(?:INBOUND(?:\s+COURSE)?|COURSE|CRS)\s+([0-3]\d{2})\b", clause)
    if match:
        inbound = schema_degree(match.group(1))

    leg_distance = None
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*NM\b", clause)
    if match:
        leg_distance = float(match.group(1))

    leg_time = None if leg_distance is not None else 1.0
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*MIN\b", clause)
    if match:
        leg_time = float(match.group(1))
        leg_distance = None

    turn = "RIGHT"
    if re.search(r"\bLEFT\s+TURNS?\b|\bLT\s+TURNS?\b", clause):
        turn = "LEFT"
    elif re.search(r"\bRIGHT\s+TURNS?\b|\bRT\s+TURNS?\b", clause):
        turn = "RIGHT"

    return {
        "inbound_course_deg": inbound,
        "leg_time_min": leg_time,
        "leg_distance_nm": leg_distance,
        "turn": turn,
    }


def clause_to_leg(clause: str, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    leg = blank_leg(index)
    evidence = {"leg_index": index, "clause": clause, "matched_rules": []}
    answers = leg["answers"]

    is_hold = bool(re.search(r"\bHOLD(?:ING)?\b", clause))
    d_ident = direct_ident(clause)
    h_ident = hold_ident(clause)
    t_ident = to_ident(clause)
    altitude = first_altitude(clause)
    radial = navaid_radial(clause)
    course = course_value(clause)

    if is_hold:
        answers["Q_terminator"] = answer("present", "HM")
        answers["Q1_fix_ident"] = answer("present", h_ident or t_ident) if h_ident or t_ident else answer("unknown")
        answers["Q3_turn"] = answer("not_applicable")
        answers["Q4_course_or_radial"] = answer("not_applicable")
        answers["Q5_hold_params"] = answer("present", hold_params(clause))
        evidence["matched_rules"].append("hold_phrase_to_HM")
    elif d_ident:
        answers["Q_terminator"] = answer("present", "DF")
        answers["Q1_fix_ident"] = answer("present", d_ident)
        answers["Q4_course_or_radial"] = answer("present", {"type": "direct"})
        evidence["matched_rules"].append("direct_phrase_to_DF")
    elif radial and t_ident:
        answers["Q_terminator"] = answer("present", "CF")
        answers["Q1_fix_ident"] = answer("present", t_ident)
        answers["Q4_course_or_radial"] = answer("present", radial)
        evidence["matched_rules"].append("radial_to_fix_to_CF")
    elif altitude is not None and not d_ident and not t_ident:
        answers["Q_terminator"] = answer("present", "CA")
        answers["Q1_fix_ident"] = answer("not_applicable")
        evidence["matched_rules"].append("climb_to_altitude_to_CA")

    if altitude is not None:
        answers["Q2_altitude_constraint"] = answer(
            "present",
            {"desc": "AT_OR_ABOVE", "altitude_ft": altitude, "altitude_2_ft": None},
        )
        evidence["matched_rules"].append("altitude_regex")

    if not is_hold:
        if re.search(r"\bLEFT\s+TURN\b|\bLT\s+TURN\b", clause):
            answers["Q3_turn"] = answer("present", "LEFT")
            evidence["matched_rules"].append("left_turn_regex")
        elif re.search(r"\bRIGHT\s+TURN\b|\bRT\s+TURN\b", clause):
            answers["Q3_turn"] = answer("present", "RIGHT")
            evidence["matched_rules"].append("right_turn_regex")

    if not is_hold and answers["Q4_course_or_radial"]["status"] != "present":
        if radial:
            answers["Q4_course_or_radial"] = answer("present", radial)
            evidence["matched_rules"].append("navaid_radial_regex")
        elif course:
            answers["Q4_course_or_radial"] = answer("present", course)
            evidence["matched_rules"].append("course_heading_regex")

    return leg, evidence


def extract_rules(row: dict[str, Any], ocr_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = normalize_text(ocr_text)
    window, window_meta = missed_approach_window(normalized)
    prediction = canonical_empty(row)
    diagnostics: dict[str, Any] = {
        "normalization": "uppercase_whitespace_dash_punctuation_only",
        "window": window_meta,
        "clauses": [],
        "evidence": [],
    }

    if not window:
        return prediction, diagnostics

    clauses = split_clauses(window)
    diagnostics["clauses"] = clauses
    if not clauses:
        return prediction, diagnostics

    legs = []
    evidence_rows = []
    for index, clause in enumerate(clauses, start=1):
        leg, evidence = clause_to_leg(clause, index)
        legs.append(leg)
        evidence_rows.append(evidence)

    prediction["missed_approach"]["leg_count"] = answer("present", len(legs))
    prediction["missed_approach"]["legs"] = legs
    diagnostics["evidence"] = evidence_rows
    return prediction, diagnostics


def summarize_method(method: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    method_results = [item for item in results if item["method"] == method]
    scored = [item["score"] for item in method_results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    return {
        "samples_total": len(method_results),
        "schema_valid": sum(1 for item in method_results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "score": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        },
        "results": method_results,
    }


def run_method(
    *,
    method: str,
    rows: list[dict[str, Any]],
    ocr_text_root: Path,
    run_dir: Path,
    validator: Draft202012Validator,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    results = []
    failures = []
    for row in rows:
        sample_id = row["pilot_sample_id"]
        chart_id = row["chart_id"]
        ocr_path = ocr_text_root / f"{chart_id}.txt"
        if not ocr_path.exists():
            failure = {
                "sample_id": sample_id,
                "chart_id": chart_id,
                "method": method,
                "error": f"missing_ocr_text:{display_path(ocr_path)}",
            }
            failures.append(failure)
            results.append(
                {
                    "method": method,
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "validation_error_count": None,
                    "score": None,
                    "failure": failure["error"],
                }
            )
            continue

        ocr_text = ocr_path.read_text(encoding="utf-8")
        prediction, diagnostics = extract_rules(row, ocr_text)
        write_json(run_dir / method / "canonical_json" / f"{chart_id}.json", prediction)
        write_json(run_dir / method / "rule_diagnostics" / f"{chart_id}.json", diagnostics)
        validation_errors = validate_canonical(prediction, validator)
        write_json(run_dir / method / "validation" / f"{chart_id}.json", validation_errors)

        item: dict[str, Any] = {
            "method": method,
            "sample_id": sample_id,
            "chart_id": chart_id,
            "validation_error_count": len(validation_errors),
            "validation_errors": validation_errors,
            "score": None,
        }
        if validation_errors:
            failures.append(
                {
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "method": method,
                    "error": "schema_validation_failed",
                }
            )
        else:
            target_path = resolve_package_path(row["canonical_proxy_gt_file"])
            target = json.loads(target_path.read_text(encoding="utf-8"))
            score = score_canonical(prediction, target)
            write_json(run_dir / method / "scores" / f"{chart_id}.json", score)
            item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
        results.append(item)
    return results, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run candidate deterministic A1/A2 OCR+Rules pilot.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--methods", default="A1,A2", help="Comma-separated subset from A1,A2.")
    parser.add_argument("--sample-manifest", type=Path, default=DATA_DIR / "pilot10_manifest.jsonl")
    parser.add_argument("--output-root", type=Path, default=RUN_OUTPUT_ROOT)
    parser.add_argument("--sample-role", default="pilot10_external_excluded_from_formal_evaluation")
    parser.add_argument("--ocr1-text-root", type=Path, default=DEFAULT_OCR1_TEXT_ROOT)
    parser.add_argument("--ocr2-text-root", type=Path, default=DEFAULT_OCR2_TEXT_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = sorted(set(methods) - {"A1", "A2"})
    if unknown:
        raise ValueError(f"Unsupported methods: {unknown}")

    run_dir = args.output_root / args.run_id
    if run_dir.exists() and not args.dry_run:
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    rows = read_jsonl(args.sample_manifest)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    run_manifest = {
        "run_id": args.run_id,
        "experiment_group": "group1_full_chart_main_extraction",
        "executed_methods": methods,
        "parameter_status": "candidate_rules_pilot_not_formal_frozen",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_manifest": display_path(args.sample_manifest),
        "sample_role": args.sample_role,
        "schema": {"path": SCHEMA_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(SCHEMA_PATH)},
        "method_boundary": {
            "allowed_inputs": [
                "chart_id",
                "airport",
                "approach_ident",
                "chart_name",
                "registered full-chart OCR text for the method",
                "canonical JSON schema contract",
            ],
            "forbidden_inputs": [
                "chart image pixels after OCR",
                "OCR from another OCR source",
                "LLM_or_VLM_output",
                "field_candidates",
                "field_to_leg_candidates",
                "gold_missed_approach_prose",
                "canonical_target_or_answer_key",
                "scorer_output",
                "CIFP_or_ARINC_424_records",
                "human_annotations",
                "previous_model_or_rule_outputs_for_same_chart",
                "web_search",
            ],
        },
        "rules": {
            "rule_id": "group1_a1_a2_ocr_rules_candidate_v1",
            "spec_path": RULE_SPEC.relative_to(ROOT).as_posix(),
            "spec_sha256": sha256_file(RULE_SPEC),
            "script_path": "scripts/run_a1_a2_rules_pilot10.py",
            "script_sha256": sha256_file(Path(__file__)),
            "target_used_for_prediction": False,
            "scorer_used_for_prediction": False,
            "llm_or_vlm_used_for_prediction": False,
            "same_rules_for_A1_and_A2": True,
        },
        "ocr_sources": {
            "A1": {
                "ocr_id": "OCR-1",
                "source": "PaddleOCR PP-OCRv5",
                "full_text_root": display_path(args.ocr1_text_root),
            },
            "A2": {
                "ocr_id": "OCR-2",
                "source": "Tesseract 5.x",
                "full_text_root": display_path(args.ocr2_text_root),
            },
        },
        "ocr_artifact_manifests": {
            "OCR-1": ocr_manifest_artifacts(args.ocr1_text_root),
            "OCR-2": ocr_manifest_artifacts(args.ocr2_text_root),
        },
        "input_artifacts": input_artifacts(rows, args.ocr1_text_root, args.ocr2_text_root),
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    if args.dry_run:
        print(f"Dry run prepared {len(rows)} samples in {run_dir}.")
        return 0

    all_results: list[dict[str, Any]] = []
    all_failures: list[dict[str, str]] = []
    if "A1" in methods:
        print("Running A1 OCR-1 + Rules", flush=True)
        results, failures = run_method(
            method="A1",
            rows=rows,
            ocr_text_root=args.ocr1_text_root,
            run_dir=run_dir,
            validator=validator,
        )
        all_results.extend(results)
        all_failures.extend(failures)
    if "A2" in methods:
        print("Running A2 OCR-2 + Rules", flush=True)
        results, failures = run_method(
            method="A2",
            rows=rows,
            ocr_text_root=args.ocr2_text_root,
            run_dir=run_dir,
            validator=validator,
        )
        all_results.extend(results)
        all_failures.extend(failures)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "parameter_status": "candidate_rules_pilot_not_formal_frozen",
        "methods": {method: summarize_method(method, all_results) for method in methods},
        "failures": all_failures,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not all_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
