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
DEFAULT_SAMPLE_MANIFEST = (
    ROOT
    / "benchmark_exports"
    / "derived"
    / "v2"
    / "formal300"
    / "split_candidates"
    / "split_50_200_50_seed20260437"
    / "sample_manifest_50_200_50_seed20260437.jsonl"
)
CHART_TO_EVIDENCE_PROMPT = ROOT / "training" / "group1_sft" / "prompts" / "chart_to_evidence.zh.md"
EVIDENCE_TO_QUESTIONNAIRE_PROMPT = ROOT / "training" / "group1_sft" / "prompts" / "evidence_to_questionnaire.zh.md"
EVIDENCE_SCHEMA = ROOT / "training" / "group1_sft" / "manifests" / "evidence_record.schema.json"
QUESTIONNAIRE_SCHEMA = ROOT / "training" / "group1_sft" / "manifests" / "evidence_questionnaire.schema.json"

QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

REGION_MAP = {
    "MISSED_APPROACH_TEXT": "MISSED_APPROACH_TEXT",
    "PLAN_VIEW": "PLAN_VIEW",
    "MISSED_APPROACH_DETAIL_AREA": "MISSED_APPROACH_DETAIL_AREA",
    "ALTITUDE_TEXT": "PROFILE_VIEW",
    "FIX_TEXT": "PROFILE_VIEW",
    "CLIMB_ARROW": "PROFILE_VIEW",
    "FIX_SYMBOL": "PROFILE_VIEW",
    "NAVAID_TEXT": "PLAN_VIEW",
    "RADIAL_TEXT": "PLAN_VIEW",
    "HEADING_TEXT": "PLAN_VIEW",
    "PATH_SEGMENT": "PLAN_VIEW",
    "TRACK_OR_RADIAL_TEXT": "PLAN_VIEW",
    "OUTBOUND_INBOUND_MARK": "PLAN_VIEW",
}

ITEM_MAP = {
    "MISSED_APPROACH_TEXT": "text_line",
    "PLAN_VIEW": "plan_view_region",
    "MISSED_APPROACH_DETAIL_AREA": "detail_area",
    "ALTITUDE_TEXT": "altitude_text",
    "FIX_TEXT": "fix_text",
    "CLIMB_ARROW": "turn_arrow",
    "FIX_SYMBOL": "fix_symbol",
    "NAVAID_TEXT": "navaid_text",
    "RADIAL_TEXT": "course_or_radial_text",
    "HEADING_TEXT": "course_or_radial_text",
    "PATH_SEGMENT": "path_segment",
    "TRACK_OR_RADIAL_TEXT": "course_or_radial_text",
    "OUTBOUND_INBOUND_MARK": "holding_pattern",
}

GENERIC_LABELS = {
    "upper coarse formal annotation: missed-approach text block",
    "coarse plan-view context for missed approach",
    "lower/profile missed-approach detail area snapped to AIP table lines",
    "detected lower detail: climb arrow",
    "detected lower detail: fix symbol",
    "detected lower detail: path segment",
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


def resolve_path(value: str, repo_root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def load_paths(paths_file: Path) -> tuple[dict[str, str], Path]:
    config = read_json(paths_file)
    repo_root = resolve_path(config.get("repo_root", str(ROOT)), ROOT)
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
    return [float(bbox[key]) for key in keys]


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


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


def compact_link(mapping: dict[str, Any]) -> dict[str, Any] | None:
    leg_index = mapping.get("canonical_leg_index")
    field_name = mapping.get("field_name")
    if not isinstance(leg_index, int) or field_name not in QUESTION_FIELDS:
        return None
    link = {
        "leg_index": leg_index,
        "candidate_leg_id": mapping.get("candidate_leg_id"),
        "leg_type": mapping.get("leg_type"),
        "field_name": field_name,
        "reviewed_value": mapping.get("final_value"),
        "evidence_role": mapping.get("evidence_role"),
        "human_confidence": mapping.get("human_confidence"),
    }
    return {key: value for key, value in link.items() if value not in (None, "", [])}


def accepted_field_links(region: dict[str, Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for mapping in region.get("accepted_mappings") or []:
        link = compact_link(mapping)
        if link is not None:
            links.append(link)
    return links


def region_to_evidence_item(region: dict[str, Any]) -> dict[str, Any]:
    region_type = str(region.get("region_type") or "OTHER")
    source_region = REGION_MAP.get(region_type, "OTHER")
    item_type = ITEM_MAP.get(region_type, region_type.lower() or "region")
    label = normalize_spaces(region.get("label"))
    text = normalize_spaces(region.get("ocr_text")) or visible_text_from_label(label)
    links = accepted_field_links(region)

    value: dict[str, Any] = {}
    if text:
        value["visible_text"] = text
    if label:
        value["source_label"] = label
    if links:
        value["linked_fields"] = links

    notes_parts = []
    rid = region_id(region)
    if rid:
        notes_parts.append(f"region_id={rid}")
    if region.get("annotation_scope"):
        notes_parts.append(f"scope={region['annotation_scope']}")
    if region.get("review_action"):
        notes_parts.append(f"review_action={region['review_action']}")

    return {
        "source_region": source_region,
        "item_type": item_type,
        "text": text,
        "value": value if value else text,
        "bbox": bbox_to_array(region.get("bbox")),
        "confidence": 1.0 if region.get("review_action") in {None, "", "accept"} else 0.8,
        "notes": "; ".join(notes_parts) if notes_parts else None,
    }


def build_evidence_record(annotation: dict[str, Any]) -> dict[str, Any]:
    items = []
    seen = set()
    for region in annotation.get("regions") or []:
        rid = region_id(region)
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        item = region_to_evidence_item(region)
        if item["source_region"] == "OTHER" and not item["text"] and item["bbox"] is None:
            continue
        items.append(item)
    return {"chart_id": annotation["chart_id"], "evidence_items": items}


def field_evidence_links(annotation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for review in annotation.get("field_reviews") or []:
        idx = review.get("canonical_leg_index")
        field_name = review.get("field_name")
        if not isinstance(idx, int) or field_name not in QUESTION_FIELDS:
            continue
        row = {
            "field_key": review.get("field_key"),
            "leg_index": idx,
            "candidate_leg_id": review.get("candidate_leg_id"),
            "leg_type": review.get("leg_type"),
            "field_name": field_name,
            "support_mode": review.get("support_mode"),
            "review_status": review.get("review_status"),
            "required_evidence_region_ids": review.get("required_evidence_region_ids") or [],
            "secondary_evidence_region_ids": review.get("secondary_evidence_region_ids") or [],
            "evidence_region_ids": review.get("evidence_region_ids") or [],
            "evidence_source": review.get("evidence_source") or [],
        }
        rows.append({key: value for key, value in row.items() if value not in (None, "", [])})
    return rows


def build_semantics_input_bundle(annotation: dict[str, Any]) -> dict[str, Any]:
    return {
        "chart_id": annotation["chart_id"],
        "evidence_record": build_evidence_record(annotation),
        "field_evidence_links": field_evidence_links(annotation),
        "input_boundary": {
            "contains_human_confirmed_evidence": True,
            "contains_field_to_evidence_links": True,
            "answer_key_included": False,
            "scoring_material_included": False,
            "source_record_included": False,
        },
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


def make_chart_to_evidence_row(
    *,
    split: str,
    sample_id: str,
    sample: dict[str, Any],
    annotation: dict[str, Any],
    image_path: Path,
    prompt_text: str,
) -> dict[str, Any]:
    evidence = build_evidence_record(annotation)
    return {
        "sample_id": sample_id,
        "split": split,
        "chart_id": sample["chart_id"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": prompt_text},
                ],
            },
            {"role": "assistant", "content": json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))},
        ],
        "source_annotation": {
            "dataset_key": "formal300",
            "split_candidate_subset": "development",
            "annotation_source": "shujuji_export_final_by_annotator",
            "uses_region_accepted_mappings": True,
            "chart_id": sample["chart_id"],
        },
    }


def make_chart_to_evidence_eval_row(
    *,
    sample_id: str,
    sample: dict[str, Any],
    image_path: Path,
    prompt_text: str,
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "split": "evaluation",
        "chart_id": sample["chart_id"],
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
    }


def make_evidence_to_semantics_row(
    *,
    split: str,
    sample_id: str,
    sample: dict[str, Any],
    annotation: dict[str, Any],
    prompt_text: str,
    include_label: bool,
) -> dict[str, Any]:
    bundle = build_semantics_input_bundle(annotation)
    user_text = prompt_text + "\n\nEvidence bundle JSON:\n" + json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    row: dict[str, Any] = {
        "sample_id": sample_id,
        "split": split,
        "chart_id": sample["chart_id"],
        "evidence_record": bundle["evidence_record"],
        "field_evidence_links": bundle["field_evidence_links"],
        "declared_oracle_human_evidence_input": True,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": user_text}],
            }
        ],
        "source_annotation": {
            "dataset_key": "formal300",
            "annotation_source": "shujuji_export_final_by_annotator",
            "uses_region_accepted_mappings": True,
            "uses_field_reviews_as_label": include_label,
            "chart_id": sample["chart_id"],
        },
    }
    if include_label:
        questionnaire = build_questionnaire(annotation)
        row["messages"].append({"role": "assistant", "content": json.dumps(questionnaire, ensure_ascii=False, separators=(",", ":"))})
    return row


def validation_errors(value: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = sorted(validator.iter_errors(value), key=lambda err: list(err.path))
    return [(".".join(str(part) for part in err.path) or "$") + f": {err.message}" for err in errors]


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


def assert_no_eval_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations = []
    forbidden_fragments = ["canonical_answer", "target_json", "score_file", "raw_cifp", "raw_424"]
    for row in rows:
        if len(row.get("messages") or []) != 1:
            violations.append({"chart_id": row.get("chart_id"), "reason": "eval_row_has_assistant_message"})
        text = json.dumps(row, ensure_ascii=False)
        hits = [fragment for fragment in forbidden_fragments if fragment in text]
        if hits:
            violations.append({"chart_id": row.get("chart_id"), "reason": "forbidden_fragment", "hits": hits})
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Group 1 SFT train/dev JSONL from Shujuji annotation export.")
    parser.add_argument("--export-json", required=True, type=Path, help="Downloaded shujuji annotation export JSON.")
    parser.add_argument("--paths", type=Path, default=DEFAULT_PATHS)
    parser.add_argument("--split-json", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--sample-manifest", type=Path, default=DEFAULT_SAMPLE_MANIFEST)
    parser.add_argument("--train-target", type=int, default=40)
    args = parser.parse_args()

    config, repo_root = load_paths(args.paths)
    export = read_json(args.export_json)
    split = read_json(args.split_json)
    sample_rows = read_jsonl(args.sample_manifest)
    by_chart = {row["chart_id"]: row for row in sample_rows}
    annotations = {item["chart_id"]: item for item in annotation_records(export)}

    dev_split = split["splits"]["development"]
    eval_split = split["splits"]["evaluation"]
    probe_split = split["splits"]["probe"]
    train_samples, dev_samples = split_train_dev(dev_split, by_chart, args.train_target)

    prompt_chart = CHART_TO_EVIDENCE_PROMPT.read_text(encoding="utf-8").strip()
    prompt_semantics = EVIDENCE_TO_QUESTIONNAIRE_PROMPT.read_text(encoding="utf-8").strip()
    evidence_validator = Draft202012Validator(read_json(EVIDENCE_SCHEMA))
    questionnaire_validator = Draft202012Validator(read_json(QUESTIONNAIRE_SCHEMA))
    images_dir = resolve_path(config["formal_images_dir"], repo_root)

    def image_for(sample: dict[str, Any]) -> Path:
        return images_dir / by_chart[sample["chart_id"]]["image_file"]

    missing_annotations = [
        sample["chart_id"]
        for sample in dev_split + eval_split + probe_split
        if sample["chart_id"] not in annotations
    ]
    if missing_annotations:
        raise RuntimeError(f"Missing submitted annotations for {len(missing_annotations)} charts: {missing_annotations[:10]}")

    chart_train: list[dict[str, Any]] = []
    chart_dev: list[dict[str, Any]] = []
    chart_eval: list[dict[str, Any]] = []
    sem_train: list[dict[str, Any]] = []
    sem_dev: list[dict[str, Any]] = []
    sem_eval: list[dict[str, Any]] = []

    region_type_counts: Counter[str] = Counter()
    field_review_status_counts: Counter[str] = Counter()
    field_support_mode_counts: Counter[str] = Counter()
    accepted_mapping_counts: Counter[str] = Counter()
    schema_errors: list[dict[str, Any]] = []

    for split_name, samples, chart_rows, sem_rows, include_label in [
        ("train", train_samples, chart_train, sem_train, True),
        ("dev", dev_samples, chart_dev, sem_dev, True),
    ]:
        for idx, sample in enumerate(samples, 1):
            chart_id = sample["chart_id"]
            annotation = annotations[chart_id]
            for region in annotation.get("regions") or []:
                region_type_counts[region.get("region_type") or ""] += 1
                for mapping in region.get("accepted_mappings") or []:
                    accepted_mapping_counts[mapping.get("field_name") or ""] += 1
            for review in annotation.get("field_reviews") or []:
                field_review_status_counts[review.get("review_status") or ""] += 1
                field_support_mode_counts[review.get("support_mode") or ""] += 1

            chart_row = make_chart_to_evidence_row(
                split=split_name,
                sample_id=f"chart_to_evidence_{split_name}_{idx:04d}",
                sample=sample,
                annotation=annotation,
                image_path=image_for(sample),
                prompt_text=prompt_chart,
            )
            sem_row = make_evidence_to_semantics_row(
                split=split_name,
                sample_id=f"evidence_to_semantics_{split_name}_{idx:04d}",
                sample=sample,
                annotation=annotation,
                prompt_text=prompt_semantics,
                include_label=include_label,
            )
            chart_rows.append(chart_row)
            sem_rows.append(sem_row)

            evidence = json.loads(chart_row["messages"][1]["content"])
            questionnaire = json.loads(sem_row["messages"][1]["content"])
            for error in validation_errors(evidence, evidence_validator):
                schema_errors.append({"chart_id": chart_id, "artifact": "evidence_record", "error": error})
            for error in validation_errors(questionnaire, questionnaire_validator):
                schema_errors.append({"chart_id": chart_id, "artifact": "questionnaire", "error": error})

    for idx, sample in enumerate(eval_split, 1):
        chart_eval.append(
            make_chart_to_evidence_eval_row(
                sample_id=f"chart_to_evidence_eval_{idx:04d}",
                sample=sample,
                image_path=image_for(sample),
                prompt_text=prompt_chart,
            )
        )
        sem_eval.append(
            make_evidence_to_semantics_row(
                split="evaluation",
                sample_id=f"evidence_to_semantics_eval_{idx:04d}",
                sample=sample,
                annotation=annotations[sample["chart_id"]],
                prompt_text=prompt_semantics,
                include_label=False,
            )
        )

    eval_violations = assert_no_eval_labels(chart_eval) + assert_no_eval_labels(sem_eval)

    chart_train_path = Path(config["chart_to_evidence_train_jsonl"])
    chart_dev_path = Path(config["chart_to_evidence_dev_jsonl"])
    chart_eval_path = Path(config["chart_to_evidence_eval_jsonl"])
    sem_train_path = Path(config["evidence_to_semantics_train_jsonl"])
    sem_dev_path = Path(config["evidence_to_semantics_dev_jsonl"])
    sem_eval_path = Path(config["evidence_to_semantics_eval_jsonl"])
    write_jsonl(chart_train_path, chart_train)
    write_jsonl(chart_dev_path, chart_dev)
    write_jsonl(chart_eval_path, chart_eval)
    write_jsonl(sem_train_path, sem_train)
    write_jsonl(sem_dev_path, sem_dev)
    write_jsonl(sem_eval_path, sem_eval)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "export_json": str(args.export_json),
        "split_json": str(args.split_json),
        "development_count": len(dev_split),
        "evaluation_count": len(eval_split),
        "probe_count": len(probe_split),
        "train_count": len(train_samples),
        "dev_count": len(dev_samples),
        "schema_errors": schema_errors,
        "eval_input_violations": eval_violations,
        "region_type_counts_development_train_dev": dict(region_type_counts),
        "field_review_status_counts_development_train_dev": dict(field_review_status_counts),
        "field_support_mode_counts_development_train_dev": dict(field_support_mode_counts),
        "accepted_mapping_counts_development_train_dev": dict(accepted_mapping_counts),
        "outputs": {
            "chart_to_evidence_train_jsonl": str(chart_train_path),
            "chart_to_evidence_train_rows": len(chart_train),
            "chart_to_evidence_dev_jsonl": str(chart_dev_path),
            "chart_to_evidence_dev_rows": len(chart_dev),
            "chart_to_evidence_eval_jsonl": str(chart_eval_path),
            "chart_to_evidence_eval_rows": len(chart_eval),
            "evidence_to_semantics_train_jsonl": str(sem_train_path),
            "evidence_to_semantics_train_rows": len(sem_train),
            "evidence_to_semantics_dev_jsonl": str(sem_dev_path),
            "evidence_to_semantics_dev_rows": len(sem_dev),
            "evidence_to_semantics_eval_jsonl": str(sem_eval_path),
            "evidence_to_semantics_eval_rows": len(sem_eval),
        },
        "input_boundary": {
            "development_train_dev_use_field_reviews_as_labels": True,
            "evaluation_has_assistant_labels": False,
            "evaluation_contains_canonical_answer": False,
            "probe_used": False,
        },
    }
    report["ready"] = not schema_errors and not eval_violations
    report_path = Path(config["reports_dir"]) / "group1_sft_annotation_jsonl_build_report.json"
    write_json(report_path, report)

    print(
        json.dumps(
            {
                "ready": report["ready"],
                "schema_error_count": len(schema_errors),
                "eval_input_violation_count": len(eval_violations),
                "train_count": len(train_samples),
                "dev_count": len(dev_samples),
                "eval_count": len(sem_eval),
                "outputs": report["outputs"],
                "report": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
