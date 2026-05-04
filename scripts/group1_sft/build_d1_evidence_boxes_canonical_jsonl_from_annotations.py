from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATHS = ROOT / "training" / "group1_sft" / "configs" / "local_paths.local.json"
DEFAULT_SPLIT = (
    ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "split_candidates"
    / "split_50_200_50_seed20260437"
    / "splits_50_200_50_seed20260437.json"
)
D1_EVIDENCE_PROMPT = (
    ROOT
    / "training"
    / "group1_sft"
    / "prompts"
    / "d1_chart_to_evidence_boxes_and_canonical.zh.md"
)
WRAPPER_SCHEMA = (
    ROOT
    / "training"
    / "group1_sft"
    / "manifests"
    / "d1_chart_to_evidence_boxes_and_canonical.schema.json"
)
CANONICAL_SCHEMA = ROOT / "schemas" / "missed_approach_leg.schema.json"

QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

GENERIC_LABELS = {
    "upper coarse formal annotation: missed-approach text block",
    "coarse plan-view context for missed approach",
    "lower/profile missed-approach detail area snapped to AIP table lines",
    "detected lower detail: climb arrow",
    "detected lower detail: fix symbol",
    "detected lower detail: path segment",
}

CORE_REGION_ORDER = {
    "MISSED_APPROACH_TEXT": 0,
    "PLAN_VIEW": 1,
    "MISSED_APPROACH_DETAIL_AREA": 2,
    "ALTITUDE_TEXT": 3,
    "FIX_TEXT": 4,
    "CLIMB_ARROW": 5,
    "FIX_SYMBOL": 6,
    "NAVAID_TEXT": 7,
    "RADIAL_TEXT": 8,
    "HEADING_TEXT": 9,
    "TRACK_OR_RADIAL_TEXT": 10,
    "OUTBOUND_INBOUND_MARK": 11,
    "PATH_SEGMENT": 12,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
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


def resolve_path(value: str, *, repo_root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_paths(paths_file: Path) -> tuple[dict[str, str], Path]:
    config = read_json(paths_file)
    repo_root = resolve_path(config.get("repo_root", str(ROOT)), repo_root=ROOT)
    return config, repo_root


def annotation_records(export: dict[str, Any]) -> list[dict[str, Any]]:
    by_annotator = export["datasets"]["formal300"]["annotations"]["by_annotator"]
    values = by_annotator.values() if isinstance(by_annotator, dict) else by_annotator
    records: list[dict[str, Any]] = []
    for item in values:
        data = item.get("data") if isinstance(item, dict) else None
        if isinstance(data, dict) and data.get("save_mode") == "final":
            records.append(data)
    return records


def bbox_to_array(bbox: Any) -> list[float] | None:
    if not isinstance(bbox, dict):
        return None
    keys = ["x_center", "y_center", "width", "height"]
    if not all(key in bbox for key in keys):
        return None
    values = [round(float(bbox[key]), 4) for key in keys]
    if any(value < 0 or value > 1 for value in values):
        return None
    return values


def region_id(region: dict[str, Any]) -> str | None:
    value = region.get("final_region_id") or region.get("source_region_id")
    return str(value) if value else None


def visible_text_from_label(label: str) -> str | None:
    text = normalize_spaces(label)
    if not text or text in GENERIC_LABELS:
        return None
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    if "->" in text:
        text = text.split("->", 1)[0].strip()
    text = normalize_spaces(text)
    return text if text and text not in GENERIC_LABELS else None


def compact_binding(mapping: dict[str, Any]) -> dict[str, Any] | None:
    leg_index = mapping.get("canonical_leg_index")
    field_name = mapping.get("field_name")
    if not isinstance(leg_index, int) or field_name not in QUESTION_FIELDS:
        return None
    return {
        "leg_index": leg_index,
        "candidate_leg_id": mapping.get("candidate_leg_id") or None,
        "field_name": field_name,
        "evidence_role": mapping.get("evidence_role") or None,
        "human_confidence": mapping.get("human_confidence") or None,
    }


def candidate_bindings(region: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    rows: list[dict[str, Any]] = []
    for mapping in region.get("accepted_mappings") or []:
        row = compact_binding(mapping)
        if row is None:
            continue
        key = (row["leg_index"], row["candidate_leg_id"], row["field_name"], row["evidence_role"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return sorted(rows, key=lambda item: (item["leg_index"], item["field_name"], item["candidate_leg_id"] or ""))


def region_sort_key(region: dict[str, Any]) -> tuple[int, int, float, float, str]:
    bindings = candidate_bindings(region)
    region_type = str(region.get("region_type") or "OTHER")
    bbox = bbox_to_array(region.get("bbox")) or [1.0, 1.0, 1.0, 1.0]
    has_bindings = 0 if bindings else 1
    region_rank = CORE_REGION_ORDER.get(region_type, 99)
    return (has_bindings, region_rank, bbox[1], bbox[0], region_id(region) or "")


def build_evidence_boxes(annotation: dict[str, Any], *, max_boxes: int) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    seen: set[str] = set()
    regions = sorted(annotation.get("regions") or [], key=region_sort_key)
    for region in regions:
        rid = region_id(region)
        bbox = bbox_to_array(region.get("bbox"))
        if not rid or rid in seen or bbox is None:
            continue
        seen.add(rid)
        region_type = str(region.get("region_type") or "OTHER")
        if region_type not in CORE_REGION_ORDER and not candidate_bindings(region):
            continue
        label = normalize_spaces(region.get("label"))
        text = normalize_spaces(region.get("ocr_text")) or visible_text_from_label(label)
        boxes.append(
            {
                "box_id": rid,
                "bbox": bbox,
                "region_type": region_type if region_type in CORE_REGION_ORDER else "OTHER",
                "visible_text": text or None,
                "candidate_bindings": candidate_bindings(region),
            }
        )
        if len(boxes) >= max_boxes:
            break
    return boxes


def procedure_metadata(sample: dict[str, Any]) -> dict[str, Any]:
    chart_id = str(sample["chart_id"])
    approach_ident = str(sample.get("proc_ident") or (chart_id.split("_", 1)[1] if "_" in chart_id else chart_id))
    return {
        "airport": str(sample.get("airport") or chart_id[:4]),
        "approach_ident": approach_ident,
        "chart_name": str(sample.get("chart_name") or "UNKNOWN"),
    }


def build_questionnaire(annotation: dict[str, Any]) -> dict[str, Any]:
    by_leg: dict[int, dict[str, Any]] = defaultdict(dict)
    for review in annotation.get("field_reviews") or []:
        idx = review.get("canonical_leg_index")
        field_name = review.get("field_name")
        answer = review.get("canonical_answer")
        if not isinstance(idx, int) or field_name not in QUESTION_FIELDS or not isinstance(answer, dict):
            continue
        by_leg[idx][field_name] = {
            "status": answer.get("status", "unknown"),
            "value": answer.get("value"),
        }

    leg_count = max(by_leg.keys(), default=0)
    legs = []
    for idx in range(1, leg_count + 1):
        row = {"leg_index": idx}
        for field in QUESTION_FIELDS:
            row[field] = by_leg.get(idx, {}).get(field, {"status": "not_applicable", "value": None})
        legs.append(row)
    return {"leg_count": leg_count, "legs": legs}


def build_canonical(sample: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    questionnaire = build_questionnaire(annotation)
    return {
        "chart_id": sample["chart_id"],
        "procedure": procedure_metadata(sample),
        "missed_approach": {
            "leg_count": {"status": "present", "value": questionnaire["leg_count"]},
            "legs": [
                {
                    "leg_index": leg["leg_index"],
                    "answers": {field: leg[field] for field in QUESTION_FIELDS},
                }
                for leg in questionnaire["legs"]
            ],
        },
    }


def build_joint_output(sample: dict[str, Any], annotation: dict[str, Any], *, max_boxes: int) -> dict[str, Any]:
    return {
        "evidence_boxes": build_evidence_boxes(annotation, max_boxes=max_boxes),
        "canonical_prediction": build_canonical(sample, annotation),
    }


def make_training_row(
    *,
    split: str,
    sample_id: str,
    sample: dict[str, Any],
    annotation: dict[str, Any],
    image_path: Path,
    prompt_text: str,
    max_boxes: int,
) -> dict[str, Any]:
    label = build_joint_output(sample, annotation, max_boxes=max_boxes)
    return {
        "sample_id": sample_id,
        "split": split,
        "chart_id": sample["chart_id"],
        "airport": sample.get("airport"),
        "proc_ident": sample.get("proc_ident"),
        "chart_name": sample.get("chart_name"),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt_text},
                ],
            },
            {"role": "assistant", "content": json.dumps(label, ensure_ascii=False, separators=(",", ":"))},
        ],
        "source_annotation": {
            "dataset_key": "formal300",
            "split_candidate_subset": "development",
            "annotation_source": "shujuji_export_final_by_annotator",
            "uses_regions_as_evidence_box_labels": True,
            "uses_field_reviews_as_canonical_labels": True,
            "evidence_boxes_exclude_final_answer_values": True,
            "chart_id": sample["chart_id"],
        },
    }


def make_eval_row(*, sample_id: str, sample: dict[str, Any], image_path: Path, prompt_text: str) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "split": "evaluation",
        "chart_id": sample["chart_id"],
        "airport": sample.get("airport"),
        "proc_ident": sample.get("proc_ident"),
        "chart_name": sample.get("chart_name"),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
        "source_split": "evaluation",
        "target_excluded_from_input_manifest": True,
    }


def split_train_dev(
    samples: list[dict[str, Any]],
    by_chart: dict[str, dict[str, Any]],
    train_target: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        airport = str(by_chart[sample["chart_id"]].get("airport") or sample["chart_id"][:4])
        groups[airport].append(sample)
    train: list[dict[str, Any]] = []
    dev: list[dict[str, Any]] = []
    for airport in sorted(groups):
        group = groups[airport]
        if len(train) + len(group) <= train_target or not train:
            train.extend(group)
        else:
            dev.extend(group)
    if not dev and len(train) > train_target:
        dev = train[train_target:]
        train = train[:train_target]
    return train, dev


def validation_errors(value: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(value), key=lambda err: list(err.path))
    return [(".".join(str(part) for part in err.path) or "$") + f": {err.message}" for err in errors]


def assert_no_eval_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations = []
    forbidden_fragments = [
        "canonical_answer",
        "final_value",
        "target_json",
        "score_file",
        "raw_cifp",
        "raw_424",
        "assistant",
    ]
    for row in rows:
        if len(row.get("messages") or []) != 1:
            violations.append({"chart_id": row.get("chart_id"), "reason": "eval_row_has_assistant_message"})
        text = json.dumps(row, ensure_ascii=False).lower()
        hits = [fragment for fragment in forbidden_fragments if fragment in text]
        if hits:
            violations.append({"chart_id": row.get("chart_id"), "reason": "forbidden_fragment", "hits": hits})
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build D1 evidence-box-plus-canonical JSONL from development annotations."
    )
    parser.add_argument("--export-json", required=True, type=Path, help="Downloaded shujuji annotation export JSON.")
    parser.add_argument("--paths", type=Path, default=DEFAULT_PATHS)
    parser.add_argument("--split-json", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--train-target", type=int, default=40)
    parser.add_argument("--max-boxes", type=int, default=12)
    args = parser.parse_args()

    config, repo_root = load_paths(args.paths)
    export = read_json(args.export_json)
    split = read_json(args.split_json)
    formal_manifest = resolve_path(config["formal_manifest"], repo_root=repo_root)
    sample_rows = read_json(formal_manifest)
    by_chart = {row["chart_id"]: row for row in sample_rows}
    annotations = {item["chart_id"]: item for item in annotation_records(export)}
    images_dir = resolve_path(config["formal_images_dir"], repo_root=repo_root)
    prompt_text = D1_EVIDENCE_PROMPT.read_text(encoding="utf-8").strip()
    wrapper_validator = Draft202012Validator(read_json(WRAPPER_SCHEMA))
    canonical_validator = Draft202012Validator(read_json(CANONICAL_SCHEMA))

    dev_split = split["splits"]["development"]
    eval_split = split["splits"]["evaluation"]
    probe_split = split["splits"]["probe"]
    train_samples, dev_samples = split_train_dev(dev_split, by_chart, args.train_target)

    missing_annotations = [sample["chart_id"] for sample in dev_split if sample["chart_id"] not in annotations]
    if missing_annotations:
        raise RuntimeError(f"Missing development annotations for {len(missing_annotations)} charts: {missing_annotations[:10]}")

    def image_for(sample: dict[str, Any]) -> Path:
        return images_dir / by_chart[sample["chart_id"]]["image_file"]

    train_rows: list[dict[str, Any]] = []
    dev_rows: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    schema_errors: list[dict[str, Any]] = []
    region_type_counts: Counter[str] = Counter()
    box_count_by_chart: dict[str, int] = {}
    field_binding_counts: Counter[str] = Counter()

    for split_name, samples, out_rows in [
        ("train", train_samples, train_rows),
        ("dev", dev_samples, dev_rows),
    ]:
        for idx, sample in enumerate(samples, 1):
            chart_id = sample["chart_id"]
            annotation = annotations[chart_id]
            row = make_training_row(
                split=split_name,
                sample_id=f"d1_evidence_boxes_canonical_{split_name}_{idx:04d}",
                sample=by_chart[chart_id],
                annotation=annotation,
                image_path=image_for(sample),
                prompt_text=prompt_text,
                max_boxes=args.max_boxes,
            )
            out_rows.append(row)
            label = json.loads(row["messages"][1]["content"])
            box_count_by_chart[chart_id] = len(label["evidence_boxes"])
            for box in label["evidence_boxes"]:
                region_type_counts[box["region_type"]] += 1
                for binding in box["candidate_bindings"]:
                    field_binding_counts[binding["field_name"]] += 1
            for error in validation_errors(label, wrapper_validator):
                schema_errors.append({"chart_id": chart_id, "artifact": "wrapper", "error": error})
            for error in validation_errors(label["canonical_prediction"], canonical_validator):
                schema_errors.append({"chart_id": chart_id, "artifact": "canonical_prediction", "error": error})

    for idx, sample in enumerate(eval_split, 1):
        eval_rows.append(
            make_eval_row(
                sample_id=f"d1_evidence_boxes_canonical_eval_{idx:04d}",
                sample=by_chart[sample["chart_id"]],
                image_path=image_for(sample),
                prompt_text=prompt_text,
            )
        )

    eval_violations = assert_no_eval_labels(eval_rows)
    train_path = resolve_path(config["d1_evidence_boxes_train_jsonl"], repo_root=repo_root)
    dev_path = resolve_path(config["d1_evidence_boxes_dev_jsonl"], repo_root=repo_root)
    eval_path = resolve_path(config["d1_evidence_boxes_eval_jsonl"], repo_root=repo_root)
    write_jsonl(train_path, train_rows)
    write_jsonl(dev_path, dev_rows)
    write_jsonl(eval_path, eval_rows)

    reports_dir = resolve_path(config.get("reports_dir", str(train_path.parent)), repo_root=repo_root)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method_id": "D1_CHART_TO_EVIDENCE_BOXES_AND_CANONICAL",
        "export_json": str(args.export_json),
        "split_json": str(args.split_json),
        "formal_manifest": str(formal_manifest),
        "development_count": len(dev_split),
        "evaluation_count": len(eval_split),
        "probe_count": len(probe_split),
        "train_count": len(train_rows),
        "dev_count": len(dev_rows),
        "max_boxes_per_chart": args.max_boxes,
        "schema_errors": schema_errors,
        "eval_input_violations": eval_violations,
        "box_count": {
            "min": min(box_count_by_chart.values(), default=0),
            "max": max(box_count_by_chart.values(), default=0),
            "mean": sum(box_count_by_chart.values()) / len(box_count_by_chart) if box_count_by_chart else None,
        },
        "region_type_counts_train_dev": dict(sorted(region_type_counts.items())),
        "field_binding_counts_train_dev": dict(sorted(field_binding_counts.items())),
        "outputs": {
            "d1_evidence_boxes_train_jsonl": str(train_path),
            "d1_evidence_boxes_train_rows": len(train_rows),
            "d1_evidence_boxes_dev_jsonl": str(dev_path),
            "d1_evidence_boxes_dev_rows": len(dev_rows),
            "d1_evidence_boxes_eval_jsonl": str(eval_path),
            "d1_evidence_boxes_eval_rows": len(eval_rows),
        },
        "input_boundary": {
            "development_train_dev_use_regions_as_box_labels": True,
            "development_train_dev_use_field_reviews_as_canonical_labels": True,
            "evaluation_has_assistant_labels": False,
            "evaluation_contains_canonical_answer": False,
            "probe_used": False,
        },
        "ready": not schema_errors and not eval_violations,
    }
    write_json(reports_dir / "d1_evidence_boxes_canonical_jsonl_build_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
