from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


RUN_ID = "group1_formal200_D1_20260502_r4"
POLICY_ID = "d1_output_canonicalization_20260502_r4"

TERMINATORS = {
    "CA", "CF", "CI", "CR", "DF", "FA", "FM", "HA", "HF", "HM", "IF", "RF", "TF",
    "VA", "VD", "VI", "VM", "VR", "AF", "CD", "FC", "FD", "VC", "PI", "unknown",
}
QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def import_scorer(path: Path):
    spec = importlib.util.spec_from_file_location("group1_canonical_field_scorer_v2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import scorer from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_wrappers(text: str) -> tuple[str, list[str]]:
    actions: list[str] = []
    stripped = text.strip()
    if stripped != text:
        actions.append("strip_outer_whitespace")
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1]).strip()
            actions.append("strip_single_markdown_code_fence")
    return stripped, actions


def iter_json_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    stack = 0
    start: int | None = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if stack == 0:
                start = i
            stack += 1
        elif ch == "}" and stack > 0:
            stack -= 1
            if stack == 0 and start is not None:
                spans.append((start, i + 1))
                start = None
    return spans


def parse_json_objects(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    actions: list[str] = []
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            actions.append("parse_entire_raw_as_json_object")
            return [obj], actions
        actions.append(f"parse_entire_raw_non_object:{type(obj).__name__}")
        return [], actions
    except Exception:
        pass

    spans = iter_json_spans(text)
    actions.append(f"extract_json_object_candidates:{len(spans)}")
    objects: list[dict[str, Any]] = []
    for start, end in spans:
        try:
            obj = json.loads(text[start:end])
        except Exception:
            continue
        if isinstance(obj, dict):
            objects.append(obj)
    return objects, actions


def split_chart_id(chart_id: Any) -> tuple[str, str]:
    if isinstance(chart_id, str) and "_" in chart_id:
        return tuple(chart_id.split("_", 1))  # type: ignore[return-value]
    if isinstance(chart_id, str):
        return chart_id[:4], ""
    return "", ""


def answer_unknown() -> dict[str, Any]:
    return {"status": "unknown", "value": None}


def answer_not_applicable() -> dict[str, Any]:
    return {"status": "not_applicable", "value": None}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def to_number(value: Any) -> float | None:
    if is_number(value):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            return float(text)
        except ValueError:
            return None
    return None


def to_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            f = float(text)
        except ValueError:
            return None
        if f.is_integer():
            return int(f)
    return None


def valid_status(status: Any) -> bool:
    return status in {"present", "not_applicable", "not_observable", "unknown"}


def normalize_status(answer: Any, actions: list[str], field_path: str) -> tuple[str, Any]:
    if not isinstance(answer, dict):
        actions.append(f"fallback_non_object_answer:{field_path}")
        return "unknown", None
    status = answer.get("status")
    value = answer.get("value")
    if not valid_status(status):
        actions.append(f"fallback_invalid_status:{field_path}")
        return "unknown", None
    if status != "present":
        if value is not None:
            actions.append(f"null_value_for_non_present:{field_path}")
        return status, None
    if value is None:
        actions.append(f"fallback_present_null_value:{field_path}")
        return "unknown", None
    return status, value


def sanitize_answer(field: str, answer: Any, actions: list[str], field_path: str) -> dict[str, Any]:
    status, value = normalize_status(answer, actions, field_path)
    if status != "present":
        return {"status": status, "value": None}

    if field == "Q_terminator":
        if isinstance(value, str) and value in TERMINATORS:
            return {"status": "present", "value": value}
        actions.append(f"fallback_invalid_terminator:{field_path}")
        return answer_unknown()

    if field == "Q1_fix_ident":
        if isinstance(value, str) and 1 <= len(value) <= 5:
            return {"status": "present", "value": value}
        actions.append(f"fallback_invalid_fix_ident:{field_path}")
        return answer_unknown()

    if field == "Q2_altitude_constraint":
        if isinstance(value, dict):
            desc = value.get("desc")
            alt1 = to_int_or_none(value.get("altitude_ft"))
            alt2 = to_int_or_none(value.get("altitude_2_ft"))
            if desc in {"AT", "AT_OR_ABOVE", "AT_OR_BELOW", "BETWEEN"}:
                return {
                    "status": "present",
                    "value": {"desc": desc, "altitude_ft": alt1, "altitude_2_ft": alt2},
                }
        actions.append(f"fallback_invalid_altitude:{field_path}")
        return answer_unknown()

    if field == "Q3_turn":
        if value in {"LEFT", "RIGHT"}:
            return {"status": "present", "value": value}
        actions.append(f"fallback_invalid_turn:{field_path}")
        return answer_unknown()

    if field == "Q4_course_or_radial":
        if isinstance(value, dict):
            typ = value.get("type")
            if typ == "direct":
                return {"status": "present", "value": {"type": "direct"}}
            if typ == "course_deg":
                course = to_number(value.get("course_deg"))
                if course is not None and 0 <= course <= 359.9:
                    return {"status": "present", "value": {"type": "course_deg", "course_deg": course}}
            if typ == "navaid_radial":
                radial = to_number(value.get("radial_deg"))
                navaid = value.get("navaid")
                direction = value.get("direction")
                if (
                    isinstance(navaid, str)
                    and 1 <= len(navaid) <= 5
                    and radial is not None
                    and 0 <= radial <= 359.9
                    and direction in {"outbound", "inbound"}
                ):
                    return {
                        "status": "present",
                        "value": {
                            "type": "navaid_radial",
                            "navaid": navaid,
                            "radial_deg": radial,
                            "direction": direction,
                        },
                    }
        actions.append(f"fallback_invalid_course_or_radial:{field_path}")
        return answer_unknown()

    if field == "Q5_hold_params":
        if isinstance(value, dict):
            inbound = to_number(value.get("inbound_course_deg"))
            if inbound is not None and not (0 <= inbound <= 359.9):
                actions.append(f"null_invalid_hold_inbound:{field_path}")
                inbound = None
            leg_time = to_number(value.get("leg_time_min"))
            if leg_time is not None and leg_time <= 0:
                actions.append(f"null_invalid_hold_time:{field_path}")
                leg_time = None
            leg_distance = to_number(value.get("leg_distance_nm"))
            if leg_distance is not None and leg_distance <= 0:
                actions.append(f"null_invalid_hold_distance:{field_path}")
                leg_distance = None
            turn = value.get("turn")
            if turn not in {"LEFT", "RIGHT", None}:
                actions.append(f"null_invalid_hold_turn:{field_path}")
                turn = None
            return {
                "status": "present",
                "value": {
                    "inbound_course_deg": inbound,
                    "leg_time_min": leg_time,
                    "leg_distance_nm": leg_distance,
                    "turn": turn,
                },
            }
        actions.append(f"fallback_invalid_hold:{field_path}")
        return answer_unknown()

    actions.append(f"fallback_unknown_field:{field_path}")
    return answer_unknown()


def sanitize_leg(leg: Any, index: int, actions: list[str]) -> dict[str, Any]:
    if not isinstance(leg, dict):
        actions.append(f"fallback_non_object_leg:{index}")
        answers = {}
    else:
        answers = leg.get("answers")
        if not isinstance(answers, dict):
            actions.append(f"fallback_missing_answers:{index}")
            answers = {}
    sanitized_answers: dict[str, Any] = {}
    for field in QUESTION_FIELDS:
        if field not in answers:
            actions.append(f"fill_missing_answer:legs[{index}].{field}")
            sanitized_answers[field] = answer_unknown()
        else:
            sanitized_answers[field] = sanitize_answer(
                field,
                answers[field],
                actions,
                f"missed_approach.legs[{index}].answers.{field}",
            )
    return {"leg_index": index, "answers": sanitized_answers}


def sanitize_leg_count(value: Any, actions: list[str], len_legs: int) -> dict[str, Any]:
    if isinstance(value, dict):
        status = value.get("status")
        raw_count = to_int_or_none(value.get("value"))
        if status == "present" and raw_count is not None:
            if raw_count != len_legs:
                actions.append("set_leg_count_to_len_legs")
            return {"status": "present", "value": len_legs}
        if len_legs:
            actions.append("set_leg_count_from_legs")
            return {"status": "present", "value": len_legs}
        if valid_status(status):
            return {"status": status, "value": None}
    elif isinstance(value, int):
        if value != len_legs:
            actions.append("set_leg_count_to_len_legs")
        return {"status": "present", "value": len_legs}
    if len_legs:
        actions.append("set_leg_count_from_legs")
        return {"status": "present", "value": len_legs}
    return answer_unknown()


def apply_manifest_envelope(obj: dict[str, Any], meta: dict[str, Any], actions: list[str]) -> dict[str, Any]:
    chart_id = meta["chart_id"]
    airport = meta.get("airport") or split_chart_id(chart_id)[0]
    approach_ident = meta.get("proc_ident") or split_chart_id(chart_id)[1]
    chart_name = meta.get("chart_name") or ""
    out = copy.deepcopy(obj)
    if out.get("chart_id") != chart_id:
        actions.append("set_manifest_chart_id_envelope")
    out["chart_id"] = chart_id
    out["procedure"] = {
        "airport": airport,
        "approach_ident": approach_ident,
        "chart_name": chart_name,
    }
    return out


def force_canonical_schema(obj: dict[str, Any], meta: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    actions: list[str] = []
    out = apply_manifest_envelope(obj, meta, actions)
    missed = out.get("missed_approach")
    if not isinstance(missed, dict):
        actions.append("fallback_missing_missed_approach")
        missed = {}
    raw_legs = missed.get("legs")
    if not isinstance(raw_legs, list):
        actions.append("fallback_missing_legs")
        raw_legs = []
    legs = [sanitize_leg(leg, idx, actions) for idx, leg in enumerate(raw_legs, start=1)]
    leg_count = sanitize_leg_count(missed.get("leg_count"), actions, len(legs))
    out["missed_approach"] = {"leg_count": leg_count, "legs": legs}
    return out, actions


def canonicalize_one(obj: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    actions: list[str] = []
    current = copy.deepcopy(obj)
    if {"chart_id", "leg_count", "legs"}.issubset(current) and "missed_approach" not in current:
        airport, approach_ident = split_chart_id(current.get("chart_id"))
        leg_count = current.get("leg_count")
        if isinstance(leg_count, int):
            leg_count = {"status": "present", "value": leg_count}
            actions.append("wrap_integer_leg_count")
        current = {
            "chart_id": current.get("chart_id"),
            "procedure": {
                "airport": airport,
                "approach_ident": current.get("approach_ident") or current.get("approach") or approach_ident,
                "chart_name": current.get("chart_name") or "",
            },
            "missed_approach": {
                "leg_count": leg_count,
                "legs": current.get("legs"),
            },
        }
        actions.append("wrap_short_raw_format_to_canonical")
        return current, actions

    if {"chart_id", "procedure", "missed_approach"}.issubset(current):
        extra = sorted(set(current) - {"chart_id", "procedure", "missed_approach"})
        if extra:
            for key in extra:
                current.pop(key, None)
            actions.append("drop_extra_top_level_fields:" + ",".join(extra))
        missed = current.get("missed_approach")
        if isinstance(missed, dict) and isinstance(missed.get("leg_count"), int):
            missed["leg_count"] = {"status": "present", "value": missed["leg_count"]}
            actions.append("wrap_integer_missed_approach_leg_count")
        return current, actions

    actions.append("raw_object_not_convertible_to_canonical_shape")
    return current, actions


def add_internal_merge_candidates(objects: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    actions: list[str] = []
    out = list(objects)
    metadata = [
        obj
        for obj in objects
        if isinstance(obj.get("chart_id"), str)
        and "procedure" not in obj
        and "missed_approach" not in obj
    ]
    bodies = [
        obj
        for obj in objects
        if isinstance(obj.get("procedure"), dict) and isinstance(obj.get("missed_approach"), dict)
    ]
    for meta in metadata:
        for body in bodies:
            merged = copy.deepcopy(body)
            merged["chart_id"] = meta["chart_id"]
            procedure = merged.setdefault("procedure", {})
            airport, approach_ident = split_chart_id(meta["chart_id"])
            procedure.setdefault("airport", airport)
            procedure.setdefault("approach_ident", meta.get("approach_ident") or meta.get("approach") or approach_ident)
            procedure.setdefault("chart_name", meta.get("chart_name") or "")
            out.append(merged)
            actions.append("merge_raw_internal_metadata_and_body")
    return out, actions


def validate(obj: dict[str, Any], scorer: Any, validator: Draft202012Validator) -> list[str]:
    return scorer.validate_canonical(obj, validator)


def load_jsonl_by_chart(path: Path | None) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if path is None:
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            chart_id = row.get("chart_id")
            if isinstance(chart_id, str):
                rows[chart_id] = row
    return rows


def score_summary(correct: int, total: int) -> dict[str, Any]:
    return {"correct": correct, "total": total, "accuracy": correct / total if total else None}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-manifest", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--scorer", type=Path, required=True)
    parser.add_argument("--target-v2", type=Path)
    parser.add_argument("--comparison-policy-v2", type=Path)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--method-card", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()

    out_root = args.out_root
    raw_copy_dir = out_root / "raw_text"
    canonical_dir = out_root / "canonical_json"
    scores_dir = out_root / "scores"
    validation_dir = out_root / "validation"
    reports_dir = out_root / "reports"
    configs_dir = out_root / "configs"
    for directory in [raw_copy_dir, canonical_dir, scores_dir, validation_dir, reports_dir, configs_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.policy, configs_dir / args.policy.name)
    shutil.copy2(args.method_card, configs_dir / args.method_card.name)
    shutil.copy2(Path(__file__), configs_dir / Path(__file__).name)

    scorer = import_scorer(args.scorer)
    validator = Draft202012Validator(read_json(args.schema))
    input_meta = load_jsonl_by_chart(args.input_manifest)
    target_v2 = read_json(args.target_v2) if args.target_v2 else {}
    policies = scorer.load_policy(args.comparison_policy_v2) if args.comparison_policy_v2 else {}
    rows: list[dict[str, Any]] = []
    with args.sample_manifest.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))

    per_sample: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    valid_count = 0
    scored_count = 0
    total_correct = 0
    total_fields = 0
    raw_found = 0
    raw_chart_id_mismatch = 0

    for sample in rows:
        chart_id = sample["chart_id"]
        meta = dict(sample)
        meta.update(input_meta.get(chart_id, {}))
        meta["chart_id"] = chart_id
        raw_path = args.raw_dir / f"{chart_id}.txt"
        record: dict[str, Any] = {
            "run_id": RUN_ID,
            "method": "D1",
            "policy_id": POLICY_ID,
            "sample_id": sample.get("sample_id"),
            "expected_chart_id": chart_id,
            "raw_path": str(raw_path),
            "canonical_json_path": str(canonical_dir / f"{chart_id}.json"),
            "schema_valid": False,
            "raw_output_chart_id": None,
            "final_chart_id_matches_expected": None,
            "actions": [],
            "validation_errors": [],
            "score": None,
        }
        if not raw_path.exists():
            record["validation_errors"] = ["missing raw output"]
            failures.append(record)
            per_sample.append(record)
            continue
        raw_found += 1
        shutil.copy2(raw_path, raw_copy_dir / f"{chart_id}.txt")
        text, actions = strip_wrappers(raw_path.read_text(encoding="utf-8"))
        objects, parse_actions = parse_json_objects(text)
        objects, merge_actions = add_internal_merge_candidates(objects)
        actions.extend(parse_actions)
        actions.extend(merge_actions)
        selected = None
        selected_errors: list[str] = ["no parseable JSON object"]
        selected_index: int | None = None
        selected_actions: list[str] = []
        if not objects:
            objects = [{}]
            actions.append("fallback_no_parseable_json_to_empty_canonical")
        for index, obj in enumerate(objects):
            candidate, candidate_actions = canonicalize_one(obj)
            raw_candidate_chart_id = candidate.get("chart_id")
            forced, force_actions = force_canonical_schema(candidate, meta)
            errors = validate(forced, scorer, validator)
            if selected is None:
                selected = forced
                selected_errors = errors
                selected_index = index
                selected_actions = candidate_actions + force_actions
                record["raw_output_chart_id"] = raw_candidate_chart_id
            if not errors:
                selected = forced
                selected_errors = []
                selected_index = index
                selected_actions = candidate_actions + force_actions
                record["raw_output_chart_id"] = raw_candidate_chart_id
                break

        if selected is None:
            record["actions"] = actions + ["no_parseable_json_object"]
            record["validation_errors"] = selected_errors
            failures.append(record)
            per_sample.append(record)
            continue

        actions.extend(selected_actions)
        actions.append(f"selected_candidate_index:{selected_index}")
        for action in actions:
            action_counts[action] += 1

        write_json(canonical_dir / f"{chart_id}.json", selected)
        output_chart_id = selected.get("chart_id")
        record["output_chart_id"] = output_chart_id
        record["final_chart_id_matches_expected"] = output_chart_id == chart_id
        if record.get("raw_output_chart_id") not in {None, chart_id}:
            raw_chart_id_mismatch += 1
        record["actions"] = actions
        record["validation_errors"] = selected_errors
        record["schema_valid"] = not selected_errors
        write_json(
            validation_dir / f"{chart_id}.json",
            {
                "expected_chart_id": chart_id,
                "raw_output_chart_id": record.get("raw_output_chart_id"),
                "output_chart_id": output_chart_id,
                "schema_valid": not selected_errors,
                "final_chart_id_matches_expected": output_chart_id == chart_id,
                "validation_errors": selected_errors,
                "actions": actions,
            },
        )
        if selected_errors:
            failures.append(record)
        else:
            valid_count += 1
            if target_v2 and chart_id in target_v2:
                score = scorer.score_canonical(selected, target_v2[chart_id], chart_id=chart_id, policies=policies)
                write_json(scores_dir / f"{chart_id}.json", score)
                record["score"] = {
                    "correct": score["correct"],
                    "total": score["total"],
                    "accuracy": score["accuracy"],
                }
                scored_count += 1
                total_correct += score["correct"]
                total_fields += score["total"]
        per_sample.append(record)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "method": "D1",
        "policy_id": POLICY_ID,
        "purpose": "canonicalize D-SFT raw outputs into the same fixed hierarchical canonical JSON format as the CIFP/424-derived targets",
        "samples_total": len(rows),
        "raw_outputs_found": raw_found,
        "canonical_json_written": len(list(canonical_dir.glob("*.json"))),
        "schema_valid": valid_count,
        "schema_invalid": len(rows) - valid_count,
        "samples_scored": scored_count,
        "field_level_v2_score": score_summary(total_correct, total_fields) if scored_count else None,
        "raw_chart_id_mismatch_count": raw_chart_id_mismatch,
        "final_chart_id_mismatch_count": sum(
            1 for row in per_sample if row.get("final_chart_id_matches_expected") is False
        ),
        "action_counts": dict(sorted(action_counts.items())),
        "hashes": {
            "script": sha256(Path(__file__)),
            "policy": sha256(args.policy),
            "method_card": sha256(args.method_card),
            "schema": sha256(args.schema),
            "scorer_validate_only": sha256(args.scorer),
        },
        "paths": {
            "out_root": str(out_root),
            "raw_text": str(raw_copy_dir),
            "canonical_json": str(canonical_dir),
            "scores": str(scores_dir),
            "validation": str(validation_dir),
            "reports": str(reports_dir),
        },
        "failures": [
            {
                "sample_id": row.get("sample_id"),
                "expected_chart_id": row.get("expected_chart_id"),
                "raw_output_chart_id": row.get("raw_output_chart_id"),
                "output_chart_id": row.get("output_chart_id"),
                "validation_errors": row.get("validation_errors"),
                "actions": row.get("actions"),
            }
            for row in failures
        ],
    }
    write_json(reports_dir / "D1_summary.json", summary)
    write_jsonl(reports_dir / "D1_per_sample.jsonl", per_sample)
    write_jsonl(reports_dir / "D1_failures.jsonl", failures)

    lines = [
        "# D1 输出格式规范化结果",
        "",
        f"- run_id: `{RUN_ID}`",
        f"- policy_id: `{POLICY_ID}`",
        f"- 总样本: {len(rows)}",
        f"- raw output 找到: {raw_found}",
        f"- canonical JSON 写出: {summary['canonical_json_written']}",
        f"- schema-valid: {valid_count}/{len(rows)}",
        f"- schema-invalid: {len(rows) - valid_count}",
        f"- raw chart_id mismatch 审计数量: {raw_chart_id_mismatch}",
        f"- final chart_id mismatch 数量: {summary['final_chart_id_mismatch_count']}",
    "",
        "本运行用 manifest 只固定 prediction 外壳；missed-approach 字段仍来自模型 raw output。非法字段值统一降级为合法 unknown/null，不使用 target、score 或 424 raw 修答案。",
    "",
        "## 仍然 schema-invalid 的样本",
        "",
        "| expected_chart_id | output_chart_id | 首个错误 |",
        "|---|---|---|",
    ]
    for row in failures:
        err = (row.get("validation_errors") or [""])[0]
        lines.append(f"| {row.get('expected_chart_id')} | {row.get('output_chart_id')} | `{err}` |")
    (reports_dir / "D1_summary_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
