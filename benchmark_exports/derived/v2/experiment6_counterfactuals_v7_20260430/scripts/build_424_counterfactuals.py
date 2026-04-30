#!/usr/bin/env python3
"""Build Experiment 6 chart-to-424 verification counterfactual cases.

This script reads the formal sample manifest and canonical proxy targets, then
projects each target into a candidate 424-like record. It creates positive
cases and a conservative set of single-mutation negative cases.

The output JSONL includes labels and construction metadata. It is NOT a model
input file. Use pack_verification_inputs.py before model calls.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


BUILDER_VERSION = "experiment6_counterfactual_builder_prefreeze_v7"
FIELD_MAP = {
    "path_terminator": "Q_terminator",
    "fix_ident": "Q1_fix_ident",
    "altitude_constraint": "Q2_altitude_constraint",
    "turn": "Q3_turn",
    "course_or_radial": "Q4_course_or_radial",
    "hold_params": "Q5_hold_params",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def answer(answers: Dict[str, Any], question_field: str) -> Dict[str, Any]:
    value = answers.get(question_field)
    if value is None:
        return {"status": "unknown", "value": None}
    return copy.deepcopy(value)


def project_candidate(target: Dict[str, Any]) -> Dict[str, Any]:
    legs = []
    for leg in target["missed_approach"]["legs"]:
        answers = leg["answers"]
        candidate_leg = {"leg_index": leg["leg_index"]}
        for candidate_field, question_field in FIELD_MAP.items():
            candidate_leg[candidate_field] = answer(answers, question_field)
        legs.append(candidate_leg)

    leg_count_answer = target["missed_approach"].get("leg_count", {})
    leg_count = leg_count_answer.get("value")
    if not isinstance(leg_count, int):
        leg_count = len(legs)

    return {
        "record_schema_version": "candidate_424_like_v1",
        "chart_id": target["chart_id"],
        "procedure": copy.deepcopy(target["procedure"]),
        "missed_approach": {
            "leg_count": leg_count,
            "legs": legs,
        },
    }


def field_path(leg_index: int, candidate_field: str) -> str:
    return f"missed_approach.legs[{leg_index}].{candidate_field}"


def get_present_value(leg: Dict[str, Any], candidate_field: str) -> Any:
    item = leg.get(candidate_field, {})
    if item.get("status") != "present":
        return None
    return item.get("value")


def collect_fix_values(candidate: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    for leg in candidate["missed_approach"]["legs"]:
        value = get_present_value(leg, "fix_ident")
        if isinstance(value, str) and value not in values:
            values.append(value)
    return values


def collect_altitudes(candidate: Dict[str, Any]) -> List[int]:
    values: List[int] = []
    for leg in candidate["missed_approach"]["legs"]:
        value = get_present_value(leg, "altitude_constraint")
        if isinstance(value, dict):
            for key in ("altitude_ft", "altitude_2_ft"):
                alt = value.get(key)
                if isinstance(alt, int) and alt not in values:
                    values.append(alt)
    return values


def normalize_deg(value: float) -> float:
    return round(value % 360, 1)


def collect_global_fix_pool(repo_root: Path, rows: List[Dict[str, Any]]) -> List[str]:
    pool: List[str] = []
    for row in rows:
        target_path = resolve_target_path(repo_root, row)
        target = read_json(target_path)
        candidate = project_candidate(target)
        for value in collect_fix_values(candidate):
            if value not in pool:
                pool.append(value)
    return pool


def col(line: str, a: int, b: Optional[int] = None) -> str:
    if b is None:
        b = a
    return line[a - 1 : b]


def collect_same_chart_raw_fix_pool(repo_root: Path, row: Dict[str, Any]) -> List[str]:
    """Collect same-procedure chart/CIFP fixes beyond the missed-approach target.

    The formal300 raw CIFP files include all transitions for the procedure, not
    only the final missed-approach legs. Using this pool keeps fix substitution
    within the same chart/procedure family while avoiding duplicate target-leg
    artifacts.
    """
    raw_file = row.get("raw_cifp_file")
    if not raw_file:
        return []
    path = Path(raw_file)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        return []
    pool: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("S"):
                continue
            for candidate in (col(line, 30, 34).rstrip(), col(line, 51, 54).rstrip(), col(line, 21, 25).rstrip()):
                if (
                    2 <= len(candidate) <= 5
                    and candidate.isalnum()
                    and not candidate.startswith("RW")
                    and candidate not in pool
                ):
                    pool.append(candidate)
    return pool


def choose_distractor_fix(original: str, existing: List[str], global_fix_pool: List[str]) -> Optional[str]:
    for candidate in global_fix_pool:
        if candidate != original and candidate not in existing and 2 <= len(candidate) <= 5:
            return candidate
    return None


def choose_same_chart_distractor_fix(original: str, existing: List[str]) -> Optional[str]:
    for candidate in existing:
        if candidate != original and 2 <= len(candidate) <= 5:
            return candidate
    return None


def choose_chart_pool_distractor_fix(original: str, existing: List[str], chart_fix_pool: List[str]) -> Optional[str]:
    candidates = [
        item
        for item in chart_fix_pool
        if item != original and item not in existing and 2 <= len(item) <= 5
    ]
    priority_groups = [
        [item for item in candidates if len(item) == 5 and not item.startswith("I")],
        [item for item in candidates if len(item) == 3 and not item.startswith("I")],
        [item for item in candidates if not item.startswith("I")],
        candidates,
    ]
    for group in priority_groups:
        if group:
            return group[0]
    return None


def mutate_fix_substitution(
    candidate: Dict[str, Any],
    chart_fix_pool: Optional[List[str]] = None,
) -> Optional[Tuple[Dict[str, Any], str, str]]:
    fixes = collect_fix_values(candidate)
    if not fixes or chart_fix_pool is None:
        return None
    mutated = copy.deepcopy(candidate)
    # Replace every occurrence of one missed-approach target fix with another
    # same-chart/procedure fix from the raw CIFP transition pool. This matches
    # the paper plan's same-chart fix-substitution requirement while avoiding
    # duplicate target-fix artifacts.
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "fix_ident")
        if value in fixes:
            replacement = choose_chart_pool_distractor_fix(value, fixes, chart_fix_pool)
            if replacement is None:
                return None
            changed_fields = []
            for linked_leg in mutated["missed_approach"]["legs"]:
                linked_value = get_present_value(linked_leg, "fix_ident")
                if linked_value == value:
                    linked_leg["fix_ident"]["value"] = replacement
                    changed_fields.append(field_path(linked_leg["leg_index"], "fix_ident"))
            return mutated, "|".join(changed_fields), f"replace all linked occurrences of {value} with same-chart/procedure fix {replacement}"
    return None


def mutate_altitude_perturbation(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    altitudes = collect_altitudes(candidate)
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "altitude_constraint")
        if isinstance(value, dict) and isinstance(value.get("altitude_ft"), int):
            original = value["altitude_ft"]
            alternatives = [a for a in altitudes if a != original]
            if not alternatives:
                return None
            replacement = alternatives[0]
            value["altitude_ft"] = replacement
            return mutated, field_path(leg["leg_index"], "altitude_constraint"), f"replace altitude {original} with another canonical chart altitude {replacement}"
    return None


def mutate_turn_direction_flip(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "turn")
        if value in ("LEFT", "RIGHT"):
            leg["turn"]["value"] = "LEFT" if value == "RIGHT" else "RIGHT"
            return mutated, field_path(leg["leg_index"], "turn"), f"flip turn direction from {value}"
    return None


def mutate_course_radial_error(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "course_or_radial")
        if isinstance(value, dict):
            if value.get("type") == "course_deg" and isinstance(value.get("course_deg"), (int, float)):
                original = value["course_deg"]
                value["course_deg"] = normalize_deg(float(original) + 10.0)
                return mutated, field_path(leg["leg_index"], "course_or_radial"), f"shift course from {original} by 10 degrees"
            if value.get("type") == "navaid_radial" and isinstance(value.get("radial_deg"), (int, float)):
                original = value["radial_deg"]
                value["radial_deg"] = normalize_deg(float(original) + 10.0)
                return mutated, field_path(leg["leg_index"], "course_or_radial"), f"shift radial from {original} by 10 degrees"
    return None


def mutate_holding_parameter_error(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "hold_params")
        if isinstance(value, dict):
            if value.get("turn") in ("LEFT", "RIGHT"):
                original = value["turn"]
                value["turn"] = "LEFT" if original == "RIGHT" else "RIGHT"
                return mutated, field_path(leg["leg_index"], "hold_params"), f"flip hold turn from {original}"
            if isinstance(value.get("leg_time_min"), (int, float)):
                original = value["leg_time_min"]
                value["leg_time_min"] = 1.5 if float(original) == 1.0 else 1.0
                return mutated, field_path(leg["leg_index"], "hold_params"), f"change hold leg time from {original}"
            if isinstance(value.get("inbound_course_deg"), (int, float)):
                original = value["inbound_course_deg"]
                value["inbound_course_deg"] = normalize_deg(float(original) + 10.0)
                return mutated, field_path(leg["leg_index"], "hold_params"), f"shift hold inbound course from {original}"
    return None


def mutate_implicit_hold_time_omission(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "hold_params")
        if isinstance(value, dict) and value.get("leg_time_min") == 1.0:
            value["leg_time_min"] = None
            return mutated, f"{field_path(leg['leg_index'], 'hold_params')}.value.leg_time_min", "omit default 1.0 minute hold time"
    return None


def mutate_path_terminator_substitution(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "path_terminator")
        fix_value = get_present_value(leg, "fix_ident")
        altitude_value = get_present_value(leg, "altitude_constraint")
        course_value = get_present_value(leg, "course_or_radial")
        hold_value = get_present_value(leg, "hold_params")

        replacement = None
        if value == "CA" and fix_value is None and isinstance(altitude_value, dict) and isinstance(course_value, dict):
            replacement = "VA"
        elif value == "VI" and fix_value is None and course_value is not None:
            replacement = "VM"
        elif value == "VM" and fix_value is None and course_value is not None:
            replacement = "VI"
        elif value == "HM" and fix_value is not None and isinstance(hold_value, dict):
            replacement = "HF"
        elif value == "HF" and fix_value is not None and isinstance(hold_value, dict):
            replacement = "HM"
        elif value == "CF" and fix_value is not None:
            replacement = "TF"
        elif value == "TF" and fix_value is not None:
            replacement = "CF"

        if replacement is not None:
            leg["path_terminator"]["value"] = replacement
            return mutated, field_path(leg["leg_index"], "path_terminator"), f"replace path terminator {value} with structurally plausible {replacement}"
    return None


def mutate_text_only_trap(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    """Keep text-like fix/altitude fields stable and perturb graphical/derived fields."""
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "hold_params")
        if isinstance(value, dict) and isinstance(value.get("inbound_course_deg"), (int, float)):
            original = value["inbound_course_deg"]
            value["inbound_course_deg"] = normalize_deg(float(original) + 20.0)
            return mutated, field_path(leg["leg_index"], "hold_params"), f"text-only trap: keep fix/altitude but shift hold inbound course from {original}"
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "course_or_radial")
        if isinstance(value, dict):
            if value.get("type") == "course_deg" and isinstance(value.get("course_deg"), (int, float)):
                original = value["course_deg"]
                value["course_deg"] = normalize_deg(float(original) + 20.0)
                return mutated, field_path(leg["leg_index"], "course_or_radial"), f"text-only trap: keep text-like fields but shift course from {original}"
            if value.get("type") == "navaid_radial" and isinstance(value.get("radial_deg"), (int, float)):
                original = value["radial_deg"]
                value["radial_deg"] = normalize_deg(float(original) + 20.0)
                return mutated, field_path(leg["leg_index"], "course_or_radial"), f"text-only trap: keep text-like fields but shift radial from {original}"
    return None


def mutate_424_derived_trap(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    """Perturb a 424-derived code while preserving visible fix/altitude values."""
    mutated = copy.deepcopy(candidate)
    for leg in mutated["missed_approach"]["legs"]:
        value = get_present_value(leg, "path_terminator")
        fix_value = get_present_value(leg, "fix_ident")
        hold_value = get_present_value(leg, "hold_params")
        course_value = get_present_value(leg, "course_or_radial")

        replacement = None
        if value == "HM" and fix_value is not None and isinstance(hold_value, dict):
            replacement = "HF"
        elif value == "HF" and fix_value is not None and isinstance(hold_value, dict):
            replacement = "HM"
        elif value == "CF" and fix_value is not None:
            replacement = "TF"
        elif value == "TF" and fix_value is not None:
            replacement = "CF"
        elif value == "VI" and course_value is not None and fix_value is None:
            replacement = "VM"
        elif value == "VM" and course_value is not None and fix_value is None:
            replacement = "VI"
        elif value == "CA" and fix_value is None and course_value is not None:
            replacement = "VA"

        if replacement is not None:
            leg["path_terminator"]["value"] = replacement
            return mutated, field_path(leg["leg_index"], "path_terminator"), f"424-derived trap: replace derived path terminator {value} with {replacement} while keeping visible fields"
    return None


def mutate_ca_to_df_sequence_error(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    """Omit an initial CA climb leg and express the remaining to-fix leg as DF."""
    legs = candidate["missed_approach"]["legs"]
    if len(legs) < 2:
        return None
    first = legs[0]
    second = legs[1]
    if get_present_value(first, "path_terminator") != "CA":
        return None
    next_fix = get_present_value(second, "fix_ident")
    if next_fix is None:
        return None
    mutated = copy.deepcopy(candidate)
    mlegs = mutated["missed_approach"]["legs"]
    # Removing the CA leg and making the following to-fix leg a DF keeps the
    # candidate internally plausible. Whether the climb-to-altitude segment was
    # incorrectly omitted requires chart evidence.
    del mlegs[0]
    mlegs[0]["path_terminator"]["value"] = "DF"
    for new_index, leg in enumerate(mlegs, start=1):
        leg["leg_index"] = new_index
    mutated["missed_approach"]["leg_count"] = len(mlegs)
    return mutated, "missed_approach.legs.sequence", f"CA-to-DF sequence error: omit initial CA climb leg and encode next to-fix leg as DF to {next_fix}"


def mutate_ca_omission(candidate: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str, str]]:
    mutated = copy.deepcopy(candidate)
    legs = mutated["missed_approach"]["legs"]
    for pos, leg in enumerate(list(legs)):
        if get_present_value(leg, "path_terminator") == "CA":
            removed_index = leg["leg_index"]
            del legs[pos]
            for new_index, item in enumerate(legs, start=1):
                item["leg_index"] = new_index
            mutated["missed_approach"]["leg_count"] = len(legs)
            return mutated, "missed_approach.legs.sequence", f"remove CA leg {removed_index}"
    return None


MUTATORS = [
    ("fix_substitution", mutate_fix_substitution),
    ("altitude_perturbation", mutate_altitude_perturbation),
    ("turn_direction_flip", mutate_turn_direction_flip),
    ("course_radial_error", mutate_course_radial_error),
    ("holding_parameter_error", mutate_holding_parameter_error),
    ("implicit_hold_time_omission", mutate_implicit_hold_time_omission),
    ("path_terminator_substitution", mutate_path_terminator_substitution),
    ("text_only_trap", mutate_text_only_trap),
    ("424_derived_trap", mutate_424_derived_trap),
    ("ca_to_df_sequence_error", mutate_ca_to_df_sequence_error),
    ("ca_omission", mutate_ca_omission),
]


def make_case(
    row: Dict[str, Any],
    candidate: Dict[str, Any],
    case_seq: int,
    consistent: bool,
    error_fields: List[str],
    counterfactual_type: str,
    target_sha256: str,
    mutation_rule: str,
    mutation_notes: str,
) -> Dict[str, Any]:
    return {
        "verification_case_id": f"{row['sample_id']}__vcase_{case_seq:04d}",
        "chart_id": row["chart_id"],
        "sample_id": row["sample_id"],
        "split": row["dataset_split"],
        "image_path": row["image_path"],
        "image_sha256": row["image_sha256"],
        "candidate_record": candidate,
        "label": {
            "consistent": consistent,
            "error_fields": error_fields,
            "counterfactual_type": counterfactual_type,
        },
        "construction": {
            "source_target_sha256": target_sha256,
            "builder_version": BUILDER_VERSION,
            "mutation_rule": mutation_rule,
            "mutation_notes": mutation_notes,
        },
    }


def resolve_target_path(repo_root: Path, row: Dict[str, Any]) -> Path:
    target_file = Path(row["canonical_proxy_gt_file"])
    if target_file.is_absolute():
        return target_file
    return repo_root / target_file


def build_cases(args: argparse.Namespace) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    repo_root = Path(args.repo_root).resolve()
    manifest_path = Path(args.sample_manifest).resolve()
    selected_splits = set(args.splits.split(","))
    rows = [r for r in read_jsonl(manifest_path) if r.get("dataset_split") in selected_splits]
    if args.max_charts:
        rows = rows[: args.max_charts]
    chart_fix_pools = {row["chart_id"]: collect_same_chart_raw_fix_pool(repo_root, row) for row in rows}

    cases: List[Dict[str, Any]] = []
    skipped: Dict[str, int] = {name: 0 for name, _ in MUTATORS}
    produced: Dict[str, int] = {"positive": 0, **{name: 0 for name, _ in MUTATORS}}
    case_seq = 1

    for row in rows:
        target_path = resolve_target_path(repo_root, row)
        target = read_json(target_path)
        target_sha = sha256_file(target_path)
        positive_candidate = project_candidate(target)

        cases.append(
            make_case(
                row=row,
                candidate=positive_candidate,
                case_seq=case_seq,
                consistent=True,
                error_fields=[],
                counterfactual_type="positive",
                target_sha256=target_sha,
                mutation_rule="none",
                mutation_notes="candidate projected directly from canonical proxy target",
            )
        )
        produced["positive"] += 1
        case_seq += 1

        for mutation_name, mutator in MUTATORS:
            if mutation_name == "fix_substitution":
                result = mutator(positive_candidate, chart_fix_pools.get(row["chart_id"], []))
            else:
                result = mutator(positive_candidate)
            if result is None:
                skipped[mutation_name] += 1
                continue
            mutated_candidate, err_field, notes = result
            error_fields = err_field.split("|") if "|" in err_field else [err_field]
            if stable_json_hash(mutated_candidate) == stable_json_hash(positive_candidate):
                skipped[mutation_name] += 1
                continue
            cases.append(
                make_case(
                    row=row,
                    candidate=mutated_candidate,
                    case_seq=case_seq,
                    consistent=False,
                    error_fields=error_fields,
                    counterfactual_type=mutation_name,
                    target_sha256=target_sha,
                    mutation_rule=mutation_name,
                    mutation_notes=notes,
                )
            )
            produced[mutation_name] += 1
            case_seq += 1

    summary = {
        "builder_version": BUILDER_VERSION,
        "repo_root": str(repo_root),
        "sample_manifest": str(manifest_path),
        "splits": sorted(selected_splits),
        "input_chart_count": len(rows),
        "case_count": len(cases),
        "produced_by_type": produced,
        "skipped_by_type": skipped,
        "status": "prefreeze_cases_with_labels_not_model_inputs",
    }
    return cases, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--sample-manifest", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--splits", default="development,probe,evaluation")
    parser.add_argument("--max-charts", type=int, default=0)
    args = parser.parse_args()

    cases, summary = build_cases(args)
    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")

    summary_json = Path(args.summary_json)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
