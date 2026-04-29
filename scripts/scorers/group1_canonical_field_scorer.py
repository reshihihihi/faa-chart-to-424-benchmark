from __future__ import annotations

import argparse
import json
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


def score_canonical(pred: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    rows = []
    total = 0
    correct = 0

    pred_leg_count = pred.get("missed_approach", {}).get("leg_count")
    target_leg_count = target.get("missed_approach", {}).get("leg_count")
    ok = score_answer(pred_leg_count, target_leg_count)
    rows.append(
        {"field": "leg_count", "correct": ok, "pred": pred_leg_count, "target": target_leg_count}
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
            ok = score_answer(pred_answer, target_answer)
            rows.append(
                {
                    "field": f"leg_{idx}.{field}",
                    "correct": ok,
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
            result["score"] = score_canonical(prediction, target)
        else:
            result["score"] = None

    if args.output:
        write_json(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
