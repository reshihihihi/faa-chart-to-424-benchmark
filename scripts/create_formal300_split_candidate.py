from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORMAL300_DIR = ROOT / "benchmark_exports" / "derived" / "v2" / "formal300"
DEFAULT_OUTPUT_DIR = DEFAULT_FORMAL300_DIR / "split_candidates" / "split_50_200_50_seed20260437"
SPLIT_TARGETS = {"development": 50, "evaluation": 200, "probe": 50}
STRATIFY_KEYS = ["procedure_type", "sample_source", "sample_type", "leg_count"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_leg_counts(challenge_tags_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in read_jsonl(challenge_tags_path):
        for tag in row.get("tags", []):
            if str(tag).startswith("leg_count:"):
                counts[row["sample_id"]] = int(str(tag).split(":", 1)[1])
                break
    return counts


def counter_dict(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return {str(k): v for k, v in sorted(Counter(row.get(key) for row in rows).items(), key=lambda item: str(item[0]))}


def build_desired_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[Any, float]]]:
    global_counts = {key: Counter(row.get(key) for row in rows) for key in STRATIFY_KEYS}
    total = len(rows)
    return {
        split: {
            key: {value: count * target / total for value, count in global_counts[key].items()}
            for key in STRATIFY_KEYS
        }
        for split, target in SPLIT_TARGETS.items()
    }


def balance_score(assignments: dict[str, list[dict[str, Any]]], desired: dict[str, dict[str, dict[Any, float]]]) -> float:
    score = 0.0
    for split, target in SPLIT_TARGETS.items():
        score += abs(len(assignments[split]) - target) * 10000
    for split, rows in assignments.items():
        for key in STRATIFY_KEYS:
            counts = Counter(row.get(key) for row in rows)
            for value, desired_count in desired[split][key].items():
                weight = 5 if key == "procedure_type" else 4 if key == "leg_count" else 2 if key == "sample_source" else 1
                score += weight * abs(counts.get(value, 0) - desired_count)
    return score


def assign_by_airport(rows: list[dict[str, Any]], seed: int) -> dict[str, list[dict[str, Any]]] | None:
    desired = build_desired_counts(rows)
    by_airport: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_airport[row["airport"]].append(row)

    groups = []
    for airport, group_rows in by_airport.items():
        digest = hashlib.sha256(f"{seed}|{airport}".encode("utf-8")).hexdigest()
        rarity = sum(
            (10 if row.get("procedure_type") != "RNAV" else 0)
            + (8 if row.get("leg_count") in (2, 5) else 0)
            + (3 if row.get("sample_type") == "simple" else 0)
            for row in group_rows
        )
        groups.append((-rarity, -len(group_rows), digest, airport, group_rows))

    assignments: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLIT_TARGETS}
    for *_prefix, group_rows in sorted(groups):
        best: tuple[float, str] | None = None
        for split in SPLIT_TARGETS:
            if len(assignments[split]) + len(group_rows) > SPLIT_TARGETS[split]:
                continue
            assignments[split].extend(group_rows)
            candidate_score = balance_score(assignments, desired)
            del assignments[split][-len(group_rows) :]
            if best is None or candidate_score < best[0]:
                best = (candidate_score, split)
        if best is None:
            return None
        assignments[best[1]].extend(group_rows)

    if {split: len(rows_) for split, rows_ in assignments.items()} != SPLIT_TARGETS:
        return None
    return assignments


def find_best_assignment(rows: list[dict[str, Any]], start_seed: int, search_count: int) -> tuple[int, float, dict[str, list[dict[str, Any]]]]:
    desired = build_desired_counts(rows)
    best: tuple[int, float, dict[str, list[dict[str, Any]]]] | None = None
    for seed in range(start_seed, start_seed + search_count):
        assignments = assign_by_airport(rows, seed)
        if assignments is None:
            continue
        score = balance_score(assignments, desired)
        if best is None or score < best[1]:
            best = (seed, score, assignments)
    if best is None:
        raise RuntimeError("Could not produce an exact 50/200/50 split with airport grouping.")
    return best


def distribution_table(assignments: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, split_rows in assignments.items():
        rows.append({"split": split, "metric": "count", "value": "samples", "count": len(split_rows)})
        for key in STRATIFY_KEYS:
            for value, count in counter_dict(split_rows, key).items():
                rows.append({"split": split, "metric": key, "value": value, "count": count})
    return rows


def split_items(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"sample_id": row["sample_id"], "chart_id": row["chart_id"], "pdf_file": row["pdf_file"]}
        for row in sorted(rows, key=lambda item: item["sample_id"])
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a score-blind formal300 split candidate.")
    parser.add_argument("--formal300-dir", type=Path, default=DEFAULT_FORMAL300_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed-start", type=int, default=20260430)
    parser.add_argument("--search-count", type=int, default=300)
    args = parser.parse_args()

    formal_dir = args.formal300_dir
    rows = read_jsonl(formal_dir / "sample_manifest.jsonl")
    leg_counts = load_leg_counts(formal_dir / "challenge_tags.jsonl")
    for row in rows:
        row["previous_dataset_split"] = row.get("dataset_split")
        row["leg_count"] = leg_counts.get(row["sample_id"])

    seed, score, assignments = find_best_assignment(rows, args.seed_start, args.search_count)
    split_for_sample = {
        row["sample_id"]: split
        for split, split_rows in assignments.items()
        for row in split_rows
    }
    candidate_rows = []
    for row in sorted(rows, key=lambda item: item["sample_id"]):
        updated = dict(row)
        updated["dataset_split"] = split_for_sample[row["sample_id"]]
        updated["split_candidate_id"] = f"formal300_50_200_50_seed{seed}"
        updated["split_candidate_policy"] = "score_blind_airport_grouped_stratified"
        candidate_rows.append(updated)

    airport_sets = {split: {row["airport"] for row in split_rows} for split, split_rows in assignments.items()}
    airport_overlap = {
        f"{left}_vs_{right}": sorted(airport_sets[left] & airport_sets[right])
        for index, left in enumerate(SPLIT_TARGETS)
        for right in list(SPLIT_TARGETS)[index + 1 :]
    }
    old_evaluation_samples = {row["sample_id"] for row in rows if row.get("previous_dataset_split") == "evaluation"}
    old_eval_destination = Counter(split_for_sample[sample_id] for sample_id in old_evaluation_samples)
    old_split_to_new = {
        old_split: dict(Counter(split_for_sample[row["sample_id"]] for row in rows if row.get("previous_dataset_split") == old_split))
        for old_split in sorted({row.get("previous_dataset_split") for row in rows})
    }

    split_json = {
        "status": "candidate_not_formal_evaluated",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": f"formal300_50_200_50_seed{seed}",
        "seed": seed,
        "seed_search_start": args.seed_start,
        "seed_search_count": args.search_count,
        "selection_inputs": [
            "sample_manifest.jsonl metadata",
            "challenge_tags.jsonl leg_count tags",
        ],
        "model_result_inputs_used": False,
        "no_score_based_selection": True,
        "split_counts": {split: len(split_rows) for split, split_rows in assignments.items()},
        "split_policy": {
            "targets": SPLIT_TARGETS,
            "airport_grouping": "All samples from the same airport are assigned to one split.",
            "stratification_keys": STRATIFY_KEYS,
            "balance_objective": "Minimize metadata distribution deviation only; no model predictions or scores are read.",
        },
        "splits": {split: split_items(split_rows) for split, split_rows in assignments.items()},
    }

    audit = {
        "candidate_id": split_json["candidate_id"],
        "created_at_utc": split_json["created_at_utc"],
        "balance_score": score,
        "global_counts": {
            "samples": len(rows),
            **{key: counter_dict(rows, key) for key in STRATIFY_KEYS},
            "previous_dataset_split": counter_dict(rows, "previous_dataset_split"),
        },
        "split_distributions": {
            split: {
                "samples": len(split_rows),
                **{key: counter_dict(split_rows, key) for key in STRATIFY_KEYS},
            }
            for split, split_rows in assignments.items()
        },
        "airport_overlap": airport_overlap,
        "old_evaluation_destination_counts": dict(old_eval_destination),
        "old_split_to_new_split_counts": old_split_to_new,
        "formal75_run_status_recommendation": "Treat group1_formal_eval_20260430_r1 as superseded diagnostic evidence only.",
        "formal_readiness_note": "Use this split only after method configs, scorer, retry policy, and run manifests are frozen against this candidate id.",
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "splits_50_200_50_seed20260437.json", split_json)
    write_json(args.output_dir / "split_audit_50_200_50_seed20260437.json", audit)
    write_jsonl(args.output_dir / "sample_manifest_50_200_50_seed20260437.jsonl", candidate_rows)
    write_csv(args.output_dir / "split_distribution_50_200_50_seed20260437.csv", distribution_table(assignments))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
