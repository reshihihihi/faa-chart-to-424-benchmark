from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "missed_approach_leg.schema.json"

QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        messages.append(
            "missed_approach.leg_count: present value must equal len(missed_approach.legs)"
        )

    if isinstance(legs, list):
        for expected_index, leg in enumerate(legs, start=1):
            if isinstance(leg, dict) and leg.get("leg_index") != expected_index:
                messages.append(
                    f"missed_approach.legs[{expected_index - 1}].leg_index: expected {expected_index}"
                )

    for path, answer in iter_answer_objects(obj):
        status = answer.get("status")
        value = answer.get("value")
        if status != "present" and value is not None:
            messages.append(f"{path}: value must be null when status is {status!r}")
        if status == "present" and value is None:
            messages.append(f"{path}: value must be non-null when status is 'present'")
        if status == "present" and isinstance(value, str) and value.strip().lower() in {
            "unknown",
            "not_observable",
            "not applicable",
            "n/a",
        }:
            messages.append(f"{path}: present value must not contain a status word")

    return messages


def validate_canonical(obj: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    messages = []
    for err in errors:
        loc = ".".join(str(part) for part in err.path) or "$"
        messages.append(f"{loc}: {err.message}")
    messages.extend(validate_canonical_semantics(obj))
    return messages


def score_answer(pred: Any, target: Any) -> bool:
    return pred == target


def normalize_display_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"[\s.\-_/']", "", value.upper())


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_display_integer(value: Any) -> bool:
    return is_number(value) and abs(float(value) - round(float(value))) < 1e-9


def round_half_up_to_int(value: Any) -> int | None:
    if not is_number(value):
        return None
    return int(math.floor(float(value) + 0.5))


def score_degree_display_value(pred_value: Any, target_value: Any) -> bool:
    if pred_value == target_value:
        return True
    if not (is_number(pred_value) and is_number(target_value)):
        return False
    pred_is_int = is_display_integer(pred_value)
    target_is_int = is_display_integer(target_value)
    if pred_is_int and not target_is_int:
        return int(round(float(pred_value))) == round_half_up_to_int(target_value)
    if target_is_int and not pred_is_int:
        return round_half_up_to_int(pred_value) == int(round(float(target_value)))
    return False


def score_dict_with_relaxed_keys(
    pred_value: Any,
    target_value: Any,
    *,
    normalized_string_keys: set[str] | None = None,
    degree_display_keys: set[str] | None = None,
) -> bool:
    if not isinstance(pred_value, dict) or not isinstance(target_value, dict):
        return pred_value == target_value

    if set(pred_value) != set(target_value):
        return False

    normalized_string_keys = normalized_string_keys or set()
    degree_display_keys = degree_display_keys or set()
    for key in target_value:
        pred_item = pred_value.get(key)
        target_item = target_value.get(key)
        if key in normalized_string_keys:
            if normalize_display_string(pred_item) != normalize_display_string(target_item):
                return False
        elif key in degree_display_keys:
            if not score_degree_display_value(pred_item, target_item):
                return False
        elif pred_item != target_item:
            return False
    return True


def score_answer_narrowed_v2(pred: Any, target: Any, *, question_field: str) -> tuple[bool, str]:
    """Narrow display-equivalence policy for PR #25.

    This deliberately does not relax altitude, turn, leg alignment, hold time/distance,
    reciprocal courses, or missing/present status mismatches.
    """
    strict_ok = score_answer(pred, target)
    if strict_ok:
        return True, "strict_equal"

    if not isinstance(pred, dict) or not isinstance(target, dict):
        return False, "strict_non_answer"
    if pred.get("status") != target.get("status"):
        return False, "strict_status_mismatch"
    if pred.get("status") != "present":
        return False, "strict_non_present_value"

    pred_value = pred.get("value")
    target_value = target.get("value")
    if question_field == "Q1_fix_ident":
        ok = normalize_display_string(pred_value) == normalize_display_string(target_value)
        return ok, "normalized_string" if ok else "normalized_string_mismatch"
    if question_field == "Q4_course_or_radial":
        ok = score_dict_with_relaxed_keys(
            pred_value,
            target_value,
            normalized_string_keys={"navaid"},
            degree_display_keys={"course_deg", "radial_deg"},
        )
        return ok, "degree_display_rounding" if ok else "degree_display_rounding_mismatch"
    if question_field == "Q5_hold_params":
        ok = score_dict_with_relaxed_keys(
            pred_value,
            target_value,
            degree_display_keys={"inbound_course_deg"},
        )
        return ok, "hold_inbound_course_display_rounding" if ok else "hold_params_strict_mismatch"
    return False, "strict_only_field"


def score_answer_with_policy(
    pred: Any,
    target: Any,
    *,
    question_field: str,
    comparison_policy: str,
) -> tuple[bool, str, bool]:
    strict_ok = score_answer(pred, target)
    if comparison_policy == "strict":
        return strict_ok, "strict_equal" if strict_ok else "strict_mismatch", strict_ok
    if comparison_policy == "narrowed_v2":
        ok, reason = score_answer_narrowed_v2(pred, target, question_field=question_field)
        return ok, reason, strict_ok
    raise ValueError(f"unknown comparison_policy: {comparison_policy}")


def score_canonical(
    pred: dict[str, Any],
    target: dict[str, Any],
    *,
    comparison_policy: str = "strict",
) -> dict[str, Any]:
    rows = []
    total = 0
    correct = 0

    pred_leg_count = pred.get("missed_approach", {}).get("leg_count")
    target_leg_count = target.get("missed_approach", {}).get("leg_count")
    ok, reason, strict_ok = score_answer_with_policy(
        pred_leg_count,
        target_leg_count,
        question_field="leg_count",
        comparison_policy=comparison_policy,
    )
    rows.append(
        {
            "field": "leg_count",
            "question_field": "leg_count",
            "correct": ok,
            "strict_correct": strict_ok,
            "match_policy": reason,
            "pred": pred_leg_count,
            "target": target_leg_count,
        }
    )
    total += 1
    correct += int(ok)

    pred_legs = {
        leg.get("leg_index"): leg for leg in pred.get("missed_approach", {}).get("legs", [])
    }
    target_legs = target.get("missed_approach", {}).get("legs", [])
    for target_leg in target_legs:
        idx = target_leg["leg_index"]
        pred_leg = pred_legs.get(idx, {})
        pred_answers = pred_leg.get("answers", {})
        target_answers = target_leg.get("answers", {})
        for field in QUESTION_FIELDS:
            pred_answer = pred_answers.get(field)
            target_answer = target_answers.get(field)
            ok, reason, strict_ok = score_answer_with_policy(
                pred_answer,
                target_answer,
                question_field=field,
                comparison_policy=comparison_policy,
            )
            rows.append(
                {
                    "field": f"leg_{idx}.{field}",
                    "question_field": field,
                    "correct": ok,
                    "strict_correct": strict_ok,
                    "match_policy": reason,
                    "pred": pred_answer,
                    "target": target_answer,
                }
            )
            total += 1
            correct += int(ok)

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else None,
        "rows": rows,
        "comparison_policy": comparison_policy,
    }


def score_invalid_output(target: dict[str, Any], *, failure_type: str, failure_detail: Any) -> dict[str, Any]:
    rows = []
    target_leg_count = target.get("missed_approach", {}).get("leg_count")
    rows.append(
        {
            "field": "leg_count",
            "correct": False,
            "pred": {"failure_type": failure_type, "detail": failure_detail},
            "target": target_leg_count,
        }
    )
    target_legs = target.get("missed_approach", {}).get("legs", [])
    for target_leg in target_legs:
        idx = target_leg["leg_index"]
        target_answers = target_leg.get("answers", {})
        for field in QUESTION_FIELDS:
            rows.append(
                {
                    "field": f"leg_{idx}.{field}",
                    "correct": False,
                    "pred": {"failure_type": failure_type, "detail": failure_detail},
                    "target": target_answers.get(field),
                }
            )
    return {
        "correct": 0,
        "total": len(rows),
        "accuracy": 0.0 if rows else None,
        "rows": rows,
        "invalid_output_policy": "zero_for_all_target_fields",
        "failure_type": failure_type,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and score Group 1 canonical missed-approach JSON outputs."
    )
    parser.add_argument("--prediction", type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-validation-error", action="store_true")
    parser.add_argument(
        "--invalid-output-policy",
        default="no_score_without_valid_prediction",
        choices=["no_score_without_valid_prediction", "zero_for_all_target_fields"],
    )
    parser.add_argument(
        "--failure-type",
        choices=["parse_failure", "schema_failure", "api_failure", "missing_prediction"],
    )
    parser.add_argument(
        "--comparison-policy",
        default="strict",
        choices=["strict", "narrowed_v2"],
        help="Field comparison policy. Default strict preserves the original scorer.",
    )
    args = parser.parse_args()

    schema = load_json(args.schema)
    validator = Draft202012Validator(schema)
    if not args.prediction and not args.failure_type:
        parser.error("--prediction is required unless --failure-type is provided.")
    if args.failure_type and not args.target:
        parser.error("--target is required when --failure-type is provided.")

    prediction = load_json(args.prediction) if args.prediction else None
    pred_errors = (
        validate_canonical(prediction, validator) if isinstance(prediction, dict) else []
    )

    result: dict[str, Any] = {
        "prediction_path": str(args.prediction) if args.prediction else None,
        "schema_path": str(args.schema),
        "prediction_validation_errors": pred_errors,
        "prediction_schema_valid": bool(prediction is not None and not pred_errors),
        "invalid_output_policy": args.invalid_output_policy,
        "comparison_policy": args.comparison_policy,
    }

    exit_code = 0
    if pred_errors and args.fail_on_validation_error:
        exit_code = 1

    if args.target:
        target = load_json(args.target)
        target_errors = validate_canonical(target, validator)
        result["target_path"] = str(args.target)
        result["target_validation_errors"] = target_errors
        result["target_schema_valid"] = not target_errors
        if target_errors and args.fail_on_validation_error:
            exit_code = 1
        if args.failure_type and args.invalid_output_policy == "zero_for_all_target_fields":
            result["score"] = score_invalid_output(
                target,
                failure_type=args.failure_type,
                failure_detail=result.get("prediction_validation_errors") or args.failure_type,
            )
        elif pred_errors and args.invalid_output_policy == "zero_for_all_target_fields":
            result["score"] = score_invalid_output(
                target,
                failure_type="schema_failure",
                failure_detail=pred_errors,
            )
        elif not pred_errors and not target_errors and prediction is not None:
            result["score"] = score_canonical(
                prediction,
                target,
                comparison_policy=args.comparison_policy,
            )
        else:
            result["score"] = None

    if args.output:
        write_json(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
