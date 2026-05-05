from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas" / "missed_approach_leg.schema.json"
DEFAULT_POLICY_PATH = (
    REPO_ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "targets"
    / "scoring_equivalence_v2"
    / "comparison_policy_v2.jsonl"
)

DEGREE_KEYS = {"course_deg", "radial_deg", "inbound_course_deg"}
FACILITY_SUFFIXES = (" VORTAC", " VOR/DME", " VOR", " NDB", " TACAN", " DME")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_policy(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    policies: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            policies[(row["chart_id"], row["field_path"])] = row
    return policies


def iter_answer_objects(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        if "status" in obj and "value" in obj:
            yield path or "$", obj
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from iter_answer_objects(value, child_path)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from iter_answer_objects(value, f"{path}[{index}]")


def validate_canonical_semantics(obj: dict[str, Any]) -> list[str]:
    if not isinstance(obj, dict) or "missed_approach" not in obj:
        return []
    messages: list[str] = []
    missed = obj.get("missed_approach", {})
    legs = missed.get("legs", []) if isinstance(missed, dict) else []
    leg_count = missed.get("leg_count", {}) if isinstance(missed, dict) else {}
    if (
        isinstance(leg_count, dict)
        and leg_count.get("status") == "present"
        and leg_count.get("value") != len(legs)
    ):
        messages.append("missed_approach.leg_count: present value must equal len(missed_approach.legs)")
    if isinstance(legs, list):
        for expected_index, leg in enumerate(legs, start=1):
            if isinstance(leg, dict) and leg.get("leg_index") != expected_index:
                messages.append(f"missed_approach.legs[{expected_index - 1}].leg_index: expected {expected_index}")
    for path, answer in iter_answer_objects(obj):
        status = answer.get("status")
        value = answer.get("value")
        if status != "present" and value is not None:
            messages.append(f"{path}: value must be null when status is {status!r}")
        if status == "present" and value is None:
            messages.append(f"{path}: value must be non-null when status is 'present'")
    return messages


def validate_canonical(obj: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    messages = []
    for err in errors:
        loc = ".".join(str(part) for part in err.path) or "$"
        messages.append(f"{loc}: {err.message}")
    messages.extend(validate_canonical_semantics(obj))
    return messages


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def round_display_degree(value: float) -> int:
    rounded = int(math.floor(float(value) + 0.5))
    if rounded == 0 and value > 359.5:
        return 360
    return rounded


def normalize_string(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    out = value.strip().upper()
    out = re.sub(r"\s+", " ", out)
    out = out.replace("RWY ", "RW")
    out = out.replace("RWY", "RW")
    # Localizer identifiers are often displayed with a hyphen.
    if re.fullmatch(r"I-[A-Z0-9]+", out):
        out = out.replace("-", "")
    for suffix in FACILITY_SUFFIXES:
        if out.endswith(suffix):
            out = out[: -len(suffix)]
            break
    return out


def normalize_turn(value: Any) -> Any:
    text = normalize_string(value)
    if text in {"L", "LEFT TURN"}:
        return "LEFT"
    if text in {"R", "RIGHT TURN"}:
        return "RIGHT"
    return text


def normalize_number(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            if "." in text:
                f = float(text)
                return int(f) if f.is_integer() else f
            return int(text)
        except ValueError:
            return normalize_string(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def normalize_for_policy(value: Any, *, policy: str, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            k: normalize_for_policy(v, policy=policy, key=k)
            for k, v in sorted(value.items(), key=lambda item: item[0])
        }
    if isinstance(value, list):
        return [normalize_for_policy(v, policy=policy, key=key) for v in value]
    if key in DEGREE_KEYS and is_number(value):
        return round_display_degree(float(value))
    if key in {"altitude_ft", "altitude_2_ft", "leg_time_min", "leg_distance_nm"}:
        return normalize_number(value)
    if key == "turn" or policy == "exact_semantic_turn":
        return normalize_turn(value)
    if isinstance(value, str):
        return normalize_string(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def normalize_degree_only(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: normalize_degree_only(v, k) for k, v in sorted(value.items(), key=lambda item: item[0])}
    if isinstance(value, list):
        return [normalize_degree_only(v, key) for v in value]
    if key in DEGREE_KEYS and is_number(value):
        return round_display_degree(float(value))
    return value


def normalize_fix_answer(answer: Any) -> Any:
    if not isinstance(answer, dict):
        return answer
    status = answer.get("status")
    value = answer.get("value")
    if status != "present":
        return {"status": status, "value": value}
    return {"status": status, "value": normalize_string(value)}


def normalize_degree_answer(answer: Any) -> Any:
    if not isinstance(answer, dict):
        return answer
    status = answer.get("status")
    value = answer.get("value")
    if status != "present":
        return {"status": status, "value": value}
    return {"status": status, "value": normalize_degree_only(value)}


def score_answer(pred: Any, target: Any, policy_row: dict[str, Any] | None) -> tuple[bool, str, dict[str, Any]]:
    policy = (policy_row or {}).get("comparison_policy", "exact_status_value")
    if policy == "manual_review_required":
        return False, policy, {"manual_review_required": True}
    if policy == "normalized_string":
        pred_norm = normalize_fix_answer(pred)
        target_norm = normalize_fix_answer(target)
        return pred_norm == target_norm, policy, {"pred_normalized": pred_norm, "target_normalized": target_norm}
    if policy == "degree_display_rounding":
        pred_norm = normalize_degree_answer(pred)
        target_norm = normalize_degree_answer(target)
        return pred_norm == target_norm, policy, {"pred_normalized": pred_norm, "target_normalized": target_norm}
    return pred == target, policy, {"exact_status_value": True}


def field_path_for_answer(idx: int | None, field: str) -> str:
    if field == "leg_count":
        return "missed_approach.leg_count"
    return f"missed_approach.legs[{idx}].answers.{field}"


def score_canonical(
    pred: dict[str, Any],
    target: dict[str, Any],
    *,
    chart_id: str,
    policies: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    rows = []
    total = 0
    correct = 0

    pred_leg_count = pred.get("missed_approach", {}).get("leg_count")
    target_leg_count = target.get("missed_approach", {}).get("leg_count")
    field_path = field_path_for_answer(None, "leg_count")
    policy_row = policies.get((chart_id, field_path))
    ok, policy, detail = score_answer(pred_leg_count, target_leg_count, policy_row)
    rows.append(
        {
            "field": "leg_count",
            "field_path": field_path,
            "correct": ok,
            "comparison_policy": policy,
            "field_category": (policy_row or {}).get("field_category"),
            "pred": pred_leg_count,
            "target": target_leg_count,
            "detail": detail,
        }
    )
    total += 1
    correct += int(ok)

    pred_legs = {
        leg.get("leg_index"): leg for leg in pred.get("missed_approach", {}).get("legs", []) if isinstance(leg, dict)
    }
    target_legs = target.get("missed_approach", {}).get("legs", [])
    for target_leg in target_legs:
        idx = target_leg["leg_index"]
        pred_leg = pred_legs.get(idx, {})
        pred_answers = pred_leg.get("answers", {}) if isinstance(pred_leg, dict) else {}
        target_answers = target_leg.get("answers", {})
        for field in QUESTION_FIELDS:
            field_path = field_path_for_answer(idx, field)
            policy_row = policies.get((chart_id, field_path))
            pred_answer = pred_answers.get(field)
            target_answer = target_answers.get(field)
            ok, policy, detail = score_answer(pred_answer, target_answer, policy_row)
            rows.append(
                {
                    "field": f"leg_{idx}.{field}",
                    "field_path": field_path,
                    "correct": ok,
                    "comparison_policy": policy,
                    "field_category": (policy_row or {}).get("field_category"),
                    "pred": pred_answer,
                    "target": target_answer,
                    "detail": detail,
                }
            )
            total += 1
            correct += int(ok)

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else None,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Group 1 chart-display-aware canonical field scorer v2.")
    parser.add_argument("--prediction", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--chart-id", required=True)
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH, type=Path)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    schema = load_json(args.schema)
    validator = Draft202012Validator(schema)
    pred = load_json(args.prediction)
    target = load_json(args.target)
    policies = load_policy(args.policy)

    pred_errors = validate_canonical(pred, validator) if isinstance(pred, dict) else ["prediction is not an object"]
    target_errors = validate_canonical(target, validator) if isinstance(target, dict) else ["target is not an object"]

    result: dict[str, Any] = {
        "prediction_path": str(args.prediction),
        "target_path": str(args.target),
        "policy_path": str(args.policy),
        "schema_path": str(args.schema),
        "chart_id": args.chart_id,
        "prediction_validation_errors": pred_errors,
        "prediction_schema_valid": not pred_errors,
        "target_validation_errors": target_errors,
        "target_schema_valid": not target_errors,
        "scoring_mode": "chart_display_aware_v2",
    }
    if not pred_errors and not target_errors:
        result["score"] = score_canonical(pred, target, chart_id=args.chart_id, policies=policies)
    else:
        result["score"] = None

    if args.output:
        write_json(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["score"] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
