from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

ALLOWED_STATUSES = {"present", "not_applicable", "not_observable"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def answer(status: str, value: Any = None) -> dict[str, Any]:
    return {"status": status, "value": value}


def set_user_prompt(row: dict[str, Any], prompt_text: str) -> None:
    for item in row["messages"][0]["content"]:
        if item.get("type") == "text":
            item["text"] = prompt_text
            return
    raise ValueError(f"missing user prompt text for {row.get('sample_id')}")


def assistant_json(row: dict[str, Any]) -> dict[str, Any]:
    return json.loads(row["messages"][1]["content"])


def set_assistant_json(row: dict[str, Any], value: dict[str, Any]) -> None:
    row["messages"][1]["content"] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def validate_answer(path: str, obj: Any, errors: list[str]) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{path}: answer is not an object")
        return
    status = obj.get("status")
    value = obj.get("value")
    if status not in ALLOWED_STATUSES:
        errors.append(f"{path}: invalid status {status!r}")
    if status == "present" and value is None:
        errors.append(f"{path}: present value is null")
    if status != "present" and value is not None:
        errors.append(f"{path}: non-present value is not null")


def validate_doc(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missed = doc.get("missed_approach", {})
    leg_count = missed.get("leg_count")
    validate_answer("missed_approach.leg_count", leg_count, errors)
    legs = missed.get("legs", [])
    if not isinstance(legs, list):
        errors.append("missed_approach.legs: not an array")
        return errors
    if isinstance(leg_count, dict) and leg_count.get("status") == "present" and leg_count.get("value") != len(legs):
        errors.append("missed_approach.leg_count: present value does not equal len(legs)")
    for expected_index, leg in enumerate(legs, start=1):
        if leg.get("leg_index") != expected_index:
            errors.append(f"missed_approach.legs[{expected_index - 1}].leg_index: expected {expected_index}")
        answers = leg.get("answers", {})
        for field in QUESTION_FIELDS:
            validate_answer(f"missed_approach.legs[{expected_index - 1}].answers.{field}", answers.get(field), errors)
    return errors


def transform_doc(doc: dict[str, Any], counters: dict[str, int]) -> dict[str, Any]:
    missed = doc.get("missed_approach", {})
    for leg in missed.get("legs", []):
        answers = leg.get("answers", {})
        terminator = answers.get("Q_terminator", {})
        term_value = terminator.get("value") if isinstance(terminator, dict) else None
        q3 = answers.get("Q3_turn", {})
        if term_value in {"CF", "DF"} and isinstance(q3, dict) and q3.get("status") == "not_applicable":
            answers["Q3_turn"] = answer("present", "BOTH")
            counters["df_cf_q3_not_applicable_to_both"] += 1
        q4 = answers.get("Q4_course_or_radial", {})
        if (
            term_value == "DF"
            and isinstance(q4, dict)
            and q4.get("status") == "present"
            and isinstance(q4.get("value"), dict)
            and q4["value"].get("type") == "direct"
        ):
            answers["Q4_course_or_radial"] = answer("not_applicable")
            counters["df_q4_direct_to_not_applicable"] += 1
    return doc


def transform_rows(rows: list[dict[str, Any]], prompt_text: str, counters: dict[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=1):
        new_row = json.loads(json.dumps(row, ensure_ascii=False))
        set_user_prompt(new_row, prompt_text)
        doc = assistant_json(new_row)
        before_errors = validate_doc(doc)
        doc = transform_doc(doc, counters)
        after_errors = validate_doc(doc)
        if before_errors:
            counters["input_validation_error_rows"] += 1
        if after_errors:
            counters["output_validation_error_rows"] += 1
            failures.append(
                {
                    "row_index": row_index,
                    "sample_id": row.get("sample_id"),
                    "chart_id": doc.get("chart_id"),
                    "errors": after_errors[:20],
                }
            )
        set_assistant_json(new_row, doc)
        out.append(new_row)
    return out, failures


def select_subset(rows: list[dict[str, Any]], sample_count: int, seed: int) -> list[dict[str, Any]]:
    if sample_count > len(rows):
        raise ValueError(f"subset size {sample_count} exceeds row count {len(rows)}")
    rng = random.Random(seed)
    indices = sorted(rng.sample(range(len(rows)), sample_count))
    return [rows[index] for index in indices]


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sample_ids = [row.get("sample_id") for row in rows]
    chart_ids = []
    for row in rows:
        try:
            chart_ids.append(assistant_json(row).get("chart_id"))
        except Exception:
            chart_ids.append(None)
    return {
        "rows": len(rows),
        "sample_ids": sample_ids,
        "chart_ids": chart_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final-v2 corrected D1 train/dev JSONL and a frozen D1-50 subset.")
    parser.add_argument("--train-jsonl", required=True, type=Path)
    parser.add_argument("--dev-jsonl", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--subset-size", type=int, default=50)
    parser.add_argument("--subset-seed", type=int, default=260506)
    args = parser.parse_args()

    prompt_text = args.prompt.read_text(encoding="utf-8").strip()
    counters = {
        "df_q4_direct_to_not_applicable": 0,
        "df_cf_q3_not_applicable_to_both": 0,
        "input_validation_error_rows": 0,
        "output_validation_error_rows": 0,
    }
    train_rows, train_failures = transform_rows(read_jsonl(args.train_jsonl), prompt_text, counters)
    dev_rows, dev_failures = transform_rows(read_jsonl(args.dev_jsonl), prompt_text, counters)
    failures = train_failures + dev_failures
    if failures:
        raise SystemExit(f"final-v2 validation failed for {len(failures)} rows; first failure: {failures[0]}")

    subset_rows = select_subset(train_rows, args.subset_size, args.subset_seed)
    output_dir = args.output_dir
    train_out = output_dir / "d_sft_train500_dev100.final_v2.train500.jsonl"
    dev_out = output_dir / "d_sft_train500_dev100.final_v2.dev100.jsonl"
    subset_out = output_dir / f"d_sft_train500_dev100.final_v2.train{args.subset_size}_seed{args.subset_seed}.jsonl"
    write_jsonl(train_out, train_rows)
    write_jsonl(dev_out, dev_rows)
    write_jsonl(subset_out, subset_rows)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract": "final_v2_field_legality_no_open_unknown",
        "source_train_jsonl": str(args.train_jsonl),
        "source_train_sha256": sha256_file(args.train_jsonl),
        "source_dev_jsonl": str(args.dev_jsonl),
        "source_dev_sha256": sha256_file(args.dev_jsonl),
        "prompt": str(args.prompt),
        "prompt_sha256": sha256_file(args.prompt),
        "outputs": {
            "train500_jsonl": str(train_out),
            "train500_sha256": sha256_file(train_out),
            "dev100_jsonl": str(dev_out),
            "dev100_sha256": sha256_file(dev_out),
            "subset50_jsonl": str(subset_out),
            "subset50_sha256": sha256_file(subset_out),
        },
        "subset": {
            "size": args.subset_size,
            "seed": args.subset_seed,
            **summarize_rows(subset_rows),
        },
        "row_counts": {
            "train500": len(train_rows),
            "dev100": len(dev_rows),
            f"train{args.subset_size}": len(subset_rows),
        },
        "transform_counts": counters,
        "validation": {
            "status_unknown_allowed": False,
            "output_validation_error_rows": counters["output_validation_error_rows"],
        },
    }
    write_json(output_dir / "d1_final_v2_train500_dev100_and_subset_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
