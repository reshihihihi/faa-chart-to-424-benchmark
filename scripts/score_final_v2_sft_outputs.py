from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - optional dependency for portable scoring.
    Draft202012Validator = None  # type: ignore[assignment]


QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_POLICY_PATH = (
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


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_policy(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if path is None:
        return {}
    policies: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            policies[(row["chart_id"], row["field_path"])] = row
    return policies


def load_split_chart_ids(split_file: Path | None, split: str) -> list[str] | None:
    if split_file is None:
        return None
    data = load_json(split_file)
    if "splits" in data:
        split_rows = data["splits"].get(split)
    else:
        split_rows = data.get(split)
    if split_rows is None:
        raise KeyError(f"Split {split!r} not found in {split_file}")
    chart_ids: list[str] = []
    for row in split_rows:
        if isinstance(row, str):
            chart_ids.append(row)
        else:
            chart_ids.append(row["chart_id"])
    return chart_ids


def infer_chart_ids(targets_dir: Path, split_chart_ids: list[str] | None) -> list[str]:
    if split_chart_ids is not None:
        return split_chart_ids
    return sorted(path.stem for path in targets_dir.glob("*.json"))


def find_prediction_file(predictions_dir: Path, chart_id: str) -> Path | None:
    candidates = [
        predictions_dir / f"{chart_id}.json",
        predictions_dir / "canonical_json" / f"{chart_id}.json",
        predictions_dir / f"{chart_id}.txt",
        predictions_dir / "raw_text" / f"{chart_id}.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    recursive = list(predictions_dir.rglob(f"{chart_id}.json"))
    if recursive:
        return sorted(recursive)[0]
    recursive_txt = list(predictions_dir.rglob(f"{chart_id}.txt"))
    if recursive_txt:
        return sorted(recursive_txt)[0]
    return None


def extract_json_object(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    depth = 0
    in_string = False
    escape = False
    for pos in range(start, len(text)):
        char = text[pos]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : pos + 1])
    raise json.JSONDecodeError("No complete JSON object found", text, start)


def load_prediction(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return load_json(path)
    return extract_json_object(path.read_text(encoding="utf-8"))


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


def validate_canonical(obj: Any, validator: Any | None) -> list[str]:
    if not isinstance(obj, dict):
        return ["object is not a JSON object"]
    messages: list[str] = []
    if validator is not None:
        errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
        for err in errors:
            loc = ".".join(str(part) for part in err.path) or "$"
            messages.append(f"{loc}: {err.message}")
    messages.extend(validate_canonical_semantics(obj))
    return messages


def target_denominator(target: dict[str, Any]) -> int:
    legs = target.get("missed_approach", {}).get("legs", [])
    return 1 + len(legs) * len(QUESTION_FIELDS)


def target_leg_count(target: dict[str, Any]) -> int:
    return len(target.get("missed_approach", {}).get("legs", []))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def round_display_degree(value: float) -> int:
    rounded = int(math.floor(float(value) + 0.5))
    if rounded == 0 and value > 359.5:
        return 360
    return rounded


def normalize_string(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    out = value.strip().upper()
    out = re.sub(r"\s+", " ", out)
    out = out.replace("RWY ", "RW")
    out = out.replace("RWY", "RW")
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
    if text in {"B", "BOTH", "BOTH TURNS", "EITHER", "EITHER TURN"}:
        return "BOTH"
    return text


def normalize_number(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            parsed = float(text) if "." in text else int(text)
        except ValueError:
            return normalize_string(value)
        return int(parsed) if isinstance(parsed, float) and parsed.is_integer() else parsed
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
    if key in {"leg_time_min", "leg_distance_nm"}:
        return normalize_number(value)
    return value


def normalize_fix_answer(answer: Any) -> Any:
    if not isinstance(answer, dict):
        return answer
    status = answer.get("status")
    value = answer.get("value")
    if status != "present":
        return {"status": status, "value": value}
    return {"status": status, "value": normalize_string(value)}


def normalize_turn_answer(answer: Any) -> Any:
    if not isinstance(answer, dict):
        return answer
    status = answer.get("status")
    value = answer.get("value")
    if status != "present":
        return {"status": status, "value": value}
    return {"status": status, "value": normalize_turn(value)}


def normalize_degree_answer(answer: Any) -> Any:
    if not isinstance(answer, dict):
        return answer
    status = answer.get("status")
    value = answer.get("value")
    if status != "present":
        return {"status": status, "value": value}
    return {"status": status, "value": normalize_degree_only(value)}


def inferred_policy_for_field_path(field_path: str, target_answer: Any | None = None) -> str:
    if field_path == "missed_approach.leg_count":
        return "exact_status_value"
    if field_path.endswith(".Q1_fix_ident"):
        return "normalized_string"
    if field_path.endswith(".Q4_course_or_radial"):
        return "degree_display_rounding"
    if field_path.endswith(".Q5_hold_params"):
        if isinstance(target_answer, dict) and target_answer.get("status") == "present":
            return "degree_display_rounding"
        return "exact_status_value"
    return "exact_status_value"


def score_answer(
    pred: Any,
    target: Any,
    *,
    comparison_policy: str,
) -> tuple[bool, dict[str, Any]]:
    if comparison_policy == "manual_review_required":
        return False, {"manual_review_required": True}
    if comparison_policy == "normalized_string":
        pred_norm = normalize_fix_answer(pred)
        target_norm = normalize_fix_answer(target)
        return pred_norm == target_norm, {"pred_normalized": pred_norm, "target_normalized": target_norm}
    if comparison_policy == "degree_display_rounding":
        pred_norm = normalize_degree_answer(pred)
        target_norm = normalize_degree_answer(target)
        return pred_norm == target_norm, {"pred_normalized": pred_norm, "target_normalized": target_norm}
    if comparison_policy == "exact_semantic_turn":
        pred_norm = normalize_turn_answer(pred)
        target_norm = normalize_turn_answer(target)
        return pred_norm == target_norm, {"pred_normalized": pred_norm, "target_normalized": target_norm}
    return pred == target, {"exact_status_value": True}


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
    rows: list[dict[str, Any]] = []
    total = 0
    correct = 0

    pred_leg_count = pred.get("missed_approach", {}).get("leg_count")
    target_leg_count_answer = target.get("missed_approach", {}).get("leg_count")
    field_path = field_path_for_answer(None, "leg_count")
    policy_row = policies.get((chart_id, field_path), {})
    policy = policy_row.get("comparison_policy") or inferred_policy_for_field_path(field_path, target_leg_count_answer)
    ok, detail = score_answer(pred_leg_count, target_leg_count_answer, comparison_policy=policy)
    rows.append(
        {
            "chart_id": chart_id,
            "leg_index": None,
            "field": "leg_count",
            "field_path": field_path,
            "correct": ok,
            "comparison_policy": policy,
            "field_category": policy_row.get("field_category"),
            "pred": pred_leg_count,
            "target": target_leg_count_answer,
            "detail": detail,
        }
    )
    total += 1
    correct += int(ok)

    pred_legs = {
        leg.get("leg_index"): leg
        for leg in pred.get("missed_approach", {}).get("legs", [])
        if isinstance(leg, dict)
    }
    target_legs = target.get("missed_approach", {}).get("legs", [])
    for target_leg in target_legs:
        idx = target_leg["leg_index"]
        pred_leg = pred_legs.get(idx, {})
        pred_answers = pred_leg.get("answers", {}) if isinstance(pred_leg, dict) else {}
        target_answers = target_leg.get("answers", {})
        for field in QUESTION_FIELDS:
            field_path = field_path_for_answer(idx, field)
            policy_row = policies.get((chart_id, field_path), {})
            pred_answer = pred_answers.get(field)
            target_answer = target_answers.get(field)
            policy = policy_row.get("comparison_policy") or inferred_policy_for_field_path(field_path, target_answer)
            ok, detail = score_answer(pred_answer, target_answer, comparison_policy=policy)
            rows.append(
                {
                    "chart_id": chart_id,
                    "leg_index": idx,
                    "field": field,
                    "field_path": field_path,
                    "correct": ok,
                    "comparison_policy": policy,
                    "field_category": policy_row.get("field_category"),
                    "pred": pred_answer,
                    "target": target_answer,
                    "detail": detail,
                }
            )
            total += 1
            correct += int(ok)

    leg_exact_total = target_leg_count(target)
    leg_exact_correct = 0
    for idx in range(1, leg_exact_total + 1):
        leg_rows = [row for row in rows if row["leg_index"] == idx and row["field"] in QUESTION_FIELDS]
        leg_exact_correct += int(len(leg_rows) == len(QUESTION_FIELDS) and all(row["correct"] for row in leg_rows))

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else None,
        "procedure_exact": correct == total,
        "leg_count_correct": bool(rows and rows[0]["correct"]),
        "leg_exact_correct": leg_exact_correct,
        "leg_exact_total": leg_exact_total,
        "rows": rows,
    }


def zero_score(chart_id: str, target: dict[str, Any], reason: str) -> dict[str, Any]:
    total = target_denominator(target)
    return {
        "correct": 0,
        "total": total,
        "accuracy": 0.0 if total else None,
        "procedure_exact": False,
        "leg_count_correct": False,
        "leg_exact_correct": 0,
        "leg_exact_total": target_leg_count(target),
        "rows": [],
        "zero_score_reason": reason,
        "chart_id": chart_id,
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_accuracy_ci(
    per_sample: list[dict[str, Any]],
    *,
    n_samples: int,
    seed: int,
) -> dict[str, Any] | None:
    if n_samples <= 0 or not per_sample:
        return None
    rng = random.Random(seed)
    estimates: list[float] = []
    n = len(per_sample)
    for _ in range(n_samples):
        correct = 0
        total = 0
        for _ in range(n):
            row = per_sample[rng.randrange(n)]
            correct += int(row["correct"])
            total += int(row["total"])
        estimates.append(correct / total if total else 0.0)
    return {
        "n_bootstrap_samples": n_samples,
        "seed": seed,
        "mean": statistics.fmean(estimates),
        "ci95_low": percentile(estimates, 0.025),
        "ci95_high": percentile(estimates, 0.975),
    }


def build_validator(schema_path: Path | None) -> Any | None:
    if schema_path is None or Draft202012Validator is None:
        return None
    schema = load_json(schema_path)
    return Draft202012Validator(schema)


def resolve_default_paths(dataset_root: Path | None, args: argparse.Namespace) -> None:
    if args.policy is None and DEFAULT_REPO_POLICY_PATH.exists():
        args.policy = DEFAULT_REPO_POLICY_PATH
    if dataset_root is None:
        return
    if args.targets_dir is None:
        args.targets_dir = dataset_root / "formal300" / "targets" / "canonical_proxy_gt"
    if args.schema is None:
        args.schema = dataset_root / "schemas" / "missed_approach_leg.schema.json"
    if args.split_file is None:
        args.split_file = (
            dataset_root
            / "manifests"
            / "formal300_split_50_200_50_seed20260437"
            / "splits_50_200_50_seed20260437.json"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Score canonical SFT/D1 predictions against final-v2 formal targets. "
            "Parse or schema failures are counted as zero over the target denominator."
        )
    )
    parser.add_argument("--predictions-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--targets-dir", type=Path)
    parser.add_argument("--split-file", type=Path)
    parser.add_argument("--split", default="evaluation")
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--policy", type=Path, help="Optional comparison_policy_v2.jsonl override.")
    parser.add_argument("--chart-id", action="append", dest="chart_ids")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=260506)
    args = parser.parse_args()

    resolve_default_paths(args.dataset_root, args)
    if args.targets_dir is None:
        raise SystemExit("Either --dataset-root or --targets-dir is required.")

    targets_dir: Path = args.targets_dir
    predictions_dir: Path = args.predictions_dir
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    split_chart_ids = args.chart_ids or load_split_chart_ids(args.split_file, args.split)
    chart_ids = infer_chart_ids(targets_dir, split_chart_ids)
    policies = load_policy(args.policy)
    validator = build_validator(args.schema)

    per_sample_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    aggregate_correct = 0
    aggregate_total = 0
    procedure_exact_correct = 0
    leg_exact_correct = 0
    leg_exact_total = 0
    leg_count_correct = 0
    parse_ok = 0
    schema_valid = 0
    scored_samples = 0

    for chart_id in chart_ids:
        target_path = targets_dir / f"{chart_id}.json"
        if not target_path.exists():
            raise FileNotFoundError(f"Missing target for {chart_id}: {target_path}")
        target = load_json(target_path)
        target_errors = validate_canonical(target, validator)
        if target_errors:
            raise ValueError(f"Target validation failed for {chart_id}: {target_errors[:3]}")

        pred_path = find_prediction_file(predictions_dir, chart_id)
        pred: Any = None
        pred_errors: list[str] = []
        parse_error: str | None = None
        if pred_path is None:
            parse_error = "missing_prediction_file"
        else:
            try:
                pred = load_prediction(pred_path)
                parse_ok += 1
                pred_errors = validate_canonical(pred, validator)
                if not pred_errors:
                    schema_valid += 1
            except Exception as exc:  # noqa: BLE001 - recorded as formal parse failure.
                parse_error = f"{type(exc).__name__}: {exc}"

        if parse_error is None and not pred_errors:
            score = score_canonical(pred, target, chart_id=chart_id, policies=policies)
            scored_samples += 1
            field_rows.extend(score["rows"])
        else:
            reason = parse_error or "prediction_validation_failed"
            score = zero_score(chart_id, target, reason)
            error_rows.append(
                {
                    "chart_id": chart_id,
                    "prediction_path": str(pred_path) if pred_path else None,
                    "parse_error": parse_error,
                    "prediction_validation_errors": pred_errors,
                    "zero_score_reason": reason,
                }
            )

        sample_row = {
            "chart_id": chart_id,
            "prediction_path": str(pred_path) if pred_path else None,
            "target_path": str(target_path),
            "parse_ok": parse_error is None,
            "prediction_schema_valid": not pred_errors and parse_error is None,
            "correct": score["correct"],
            "total": score["total"],
            "accuracy": score["accuracy"],
            "procedure_exact": score["procedure_exact"],
            "leg_count_correct": score["leg_count_correct"],
            "leg_exact_correct": score["leg_exact_correct"],
            "leg_exact_total": score["leg_exact_total"],
            "zero_score_reason": score.get("zero_score_reason"),
        }
        per_sample_rows.append(sample_row)
        aggregate_correct += score["correct"]
        aggregate_total += score["total"]
        procedure_exact_correct += int(score["procedure_exact"])
        leg_count_correct += int(score["leg_count_correct"])
        leg_exact_correct += score["leg_exact_correct"]
        leg_exact_total += score["leg_exact_total"]

    summary = {
        "scoring_contract": "final_v2_field_legality_display_equivalence",
        "predictions_dir": str(predictions_dir),
        "targets_dir": str(targets_dir),
        "split_file": str(args.split_file) if args.split_file else None,
        "split": args.split,
        "schema": str(args.schema) if args.schema else None,
        "policy": str(args.policy) if args.policy else "auto_final_v2_field_policies",
        "samples_total": len(chart_ids),
        "samples_parse_ok": parse_ok,
        "samples_schema_valid": schema_valid,
        "samples_scored_without_zero_fallback": scored_samples,
        "correct": aggregate_correct,
        "total": aggregate_total,
        "accuracy": aggregate_correct / aggregate_total if aggregate_total else None,
        "procedure_exact_correct": procedure_exact_correct,
        "procedure_exact_total": len(chart_ids),
        "procedure_exact_accuracy": procedure_exact_correct / len(chart_ids) if chart_ids else None,
        "leg_count_correct": leg_count_correct,
        "leg_count_total": len(chart_ids),
        "leg_count_accuracy": leg_count_correct / len(chart_ids) if chart_ids else None,
        "leg_exact_correct": leg_exact_correct,
        "leg_exact_total": leg_exact_total,
        "leg_exact_accuracy": leg_exact_correct / leg_exact_total if leg_exact_total else None,
        "bootstrap_accuracy_ci": bootstrap_accuracy_ci(
            per_sample_rows,
            n_samples=args.bootstrap_samples,
            seed=args.bootstrap_seed,
        ),
    }
    write_json(output_dir / "aggregate_summary.json", summary)
    append_jsonl(output_dir / "per_sample_scores.jsonl", per_sample_rows)
    append_jsonl(output_dir / "field_scores.jsonl", field_rows)
    append_jsonl(output_dir / "sample_errors.jsonl", error_rows)
    write_json(
        output_dir / "run_manifest.json",
        {
            "command": "score_final_v2_sft_outputs.py",
            "outputs": [
                "aggregate_summary.json",
                "per_sample_scores.jsonl",
                "field_scores.jsonl",
                "sample_errors.jsonl",
                "run_manifest.json",
            ],
            "notes": [
                "Prediction parse/schema failures receive zero correct atoms over the target denominator.",
                "Default policies implement final-v2 field-legality/display-equivalence scoring.",
                "Pass --policy comparison_policy_v2.jsonl to reproduce a frozen policy export exactly.",
            ],
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
