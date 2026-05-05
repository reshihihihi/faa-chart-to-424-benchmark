import json
import os
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

import fitz


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SOURCE_ROOT = Path(os.environ.get("FAA_SOURCE_ROOT", REPO_ROOT))

V2604 = SOURCE_ROOT / "data/v2604_100"
PREP = SOURCE_ROOT / "data/preparation/probe2604"
CIFP_FILE = V2604 / "cifp/FAACIFP18"
CANDIDATE_POOL = V2604 / "candidate_pool.json"
SAMPLE_100 = V2604 / "sample_manifest_100.json"
PDF_ROOT = PREP / "pdfs"
FAA_PDF_CACHE = ROOT / "source_cache/faa_d_tpp_2604"

PRACTICE_SRC_MANIFEST = ROOT / "datasets/practice10/manifest.json"
PRACTICE_SRC_PRELABELS = ROOT / "datasets/practice10/prelabels"
PRACTICE_SRC_TARGETS = ROOT / "datasets/practice10/targets"

PR28_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]

HOLD_TYPES = {"HA", "HF", "HM"}
FIX_APPLICABLE_TYPES = {"CF", "DF", "TF", "AF", "FA", "FC", "FD", "FM", "HA", "HF", "HM", "IF"}
COURSE_CAPABLE_TYPES = {"CA", "CF", "FA", "FC", "FD", "FM", "TF", "VI", "VA", "VD", "VM", "VR"}
MISSED_STARTER_TYPES = {"CA", "VA", "VD", "VI", "VM", "VR"}
FINAL_FIX_LEG_TYPES = {"AF", "CF", "DF", "FA", "FC", "FD", "FM", "TF"}
TERMINATORS = {
    "CA", "CF", "CI", "CR", "DF", "FA", "FM", "HA", "HF", "HM", "IF", "RF",
    "TF", "VA", "VD", "VI", "VM", "VR", "AF", "CD", "FC", "FD", "VC", "PI",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(value):
    return (value or "").strip()


def parse_int(value):
    value = clean(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_angle(value):
    value = clean(value)
    if not value or not value.isdigit():
        return None
    return round(int(value) / 10.0, 1)


def reciprocal(angle):
    if angle is None:
        return None
    return round((angle + 180.0) % 360.0, 1)


def altitude_desc(raw):
    raw = clean(raw)
    if raw in ("", "@"):
        return "AT"
    if raw == "+":
        return "AT_OR_ABOVE"
    if raw in ("-", "V"):
        return "AT_OR_BELOW"
    if raw == "B":
        return "BETWEEN"
    return "AT"


def answer(status, value):
    return {"status": status, "value": value}


def parse_app_record(line):
    line = line.rstrip("\n")
    if not line.startswith("SUSAP") or len(line) < 94:
        return None
    if line[12] != "F":
        return None
    terminator_raw = clean(line[47:50])
    terminator = terminator_raw[:2]
    if terminator not in TERMINATORS:
        return None
    return {
        "airport": clean(line[6:10]),
        "proc_ident": clean(line[13:18]),
        "trans_ident": clean(line[19:25]),
        "seq_no": clean(line[26:29]),
        "fix_ident": clean(line[29:34]),
        "turn_dir": clean(line[43:44]),
        "terminator_raw": terminator_raw,
        "terminator": terminator,
        "recommended_navaid": clean(line[50:54]),
        "theta": parse_angle(line[62:66]),
        "rho_nm": parse_angle(line[66:70]),
        "course_deg": parse_angle(line[70:74]),
        "route_distance_nm": parse_angle(line[74:78]),
        "alt_desc_raw": clean(line[82:83]),
        "altitude1": clean(line[84:89]),
        "altitude2": clean(line[89:94]),
        "raw_record": line,
    }


def load_raw_index():
    by_proc = {}
    with CIFP_FILE.open("r", encoding="latin-1") as handle:
        for line in handle:
            record = parse_app_record(line)
            if record:
                by_proc.setdefault((record["airport"], record["proc_ident"]), []).append(record)
    for key, records in by_proc.items():
        records.sort(key=lambda item: (item["trans_ident"], int(item["seq_no"] or 0), item["raw_record"]))
    return by_proc


def select_missed_records(records, fallback_ma_count=None, proc_ident=None):
    if not records:
        return []

    groups = {}
    for record in records:
        groups.setdefault(record["trans_ident"], []).append(record)
    for group in groups.values():
        group.sort(key=lambda item: int(item["seq_no"] or 0))

    preferred = []
    seen = set()
    for trans in ["R", clean(proc_ident)[:1]]:
        if trans and trans in groups and trans not in seen:
            preferred.append(groups[trans])
            seen.add(trans)
    preferred.extend(group for trans, group in sorted(groups.items()) if trans not in seen)

    for group in preferred:
        runway_index = next((idx for idx, record in enumerate(group) if record["fix_ident"].startswith("RW")), None)
        if runway_index is not None:
            missed = group[runway_index + 1 :]
            if missed:
                return missed

        if fallback_ma_count and group:
            return group[-int(fallback_ma_count) :]

        starter_index = next(
            (
                idx for idx, record in enumerate(group[1:], start=1)
                if record["terminator"] in MISSED_STARTER_TYPES
            ),
            None,
        )
        if starter_index is not None:
            return group[starter_index:]

        hold_index = next(
            (
                idx for idx in range(len(group) - 1, -1, -1)
                if group[idx]["terminator"] in HOLD_TYPES
            ),
            None,
        )
        if hold_index is not None:
            start = hold_index
            hold_fix = group[hold_index]["fix_ident"]
            while (
                start > 0
                and group[start - 1]["fix_ident"] == hold_fix
                and group[start - 1]["terminator"] in FINAL_FIX_LEG_TYPES
            ):
                start -= 1
            return group[start:]
    return []


def q1_fix_answer(record):
    if record["terminator"] not in FIX_APPLICABLE_TYPES:
        return answer("not_applicable", None)
    return answer("present", record["fix_ident"]) if record["fix_ident"] else answer("unknown", None)


def q2_altitude_answer(record):
    altitude1 = parse_int(record["altitude1"])
    altitude2 = parse_int(record["altitude2"])
    if altitude1 is None:
        return answer("not_applicable", None)
    desc = altitude_desc(record["alt_desc_raw"])
    return answer("present", {
        "desc": desc,
        "altitude_ft": altitude1,
        "altitude_2_ft": altitude2 if desc == "BETWEEN" else None,
    })


def q3_turn_answer(record):
    if record["terminator"] in HOLD_TYPES:
        return answer("not_applicable", None)
    if record["turn_dir"] == "L":
        return answer("present", "LEFT")
    if record["turn_dir"] == "R":
        return answer("present", "RIGHT")
    if record["terminator"] in {"DF", "CF", "FA", "RF"}:
        return answer("unknown", None)
    return answer("not_applicable", None)


def q4_course_answer(record):
    terminator = record["terminator"]
    if terminator in HOLD_TYPES or terminator == "IF":
        return answer("not_applicable", None)
    if terminator == "DF":
        return answer("not_applicable", None)

    navaid = record["recommended_navaid"]
    course = record["course_deg"]
    if navaid and course is not None:
        if terminator in {"CF", "FC", "FD"}:
            return answer("present", {
                "type": "navaid_radial",
                "navaid": navaid,
                "radial_deg": reciprocal(course),
                "direction": "inbound",
            })
        if terminator in {"FA", "FM"}:
            return answer("present", {
                "type": "navaid_radial",
                "navaid": navaid,
                "radial_deg": course,
                "direction": "outbound",
            })

    if terminator in COURSE_CAPABLE_TYPES and course is not None:
        return answer("present", {"type": "course_deg", "course_deg": course})
    if terminator in COURSE_CAPABLE_TYPES:
        return answer("unknown", None)
    return answer("not_applicable", None)


def q5_hold_answer(record):
    if record["terminator"] not in HOLD_TYPES:
        return answer("not_applicable", None)
    raw_leg = clean(record["raw_record"][74:78])
    leg_time = None
    leg_distance = None
    if raw_leg.startswith("T"):
        leg_time_raw = parse_int(raw_leg[1:])
        leg_time = leg_time_raw / 10.0 if leg_time_raw is not None else None
    elif raw_leg.isdigit() and parse_int(raw_leg):
        leg_distance = parse_int(raw_leg) / 10.0
    turn = "LEFT" if record["turn_dir"] == "L" else "RIGHT" if record["turn_dir"] == "R" else None
    return answer("present", {
        "inbound_course_deg": record["course_deg"],
        "leg_time_min": leg_time,
        "leg_distance_nm": leg_distance,
        "turn": turn,
    })


def canonical_for_record(record, leg_index):
    return {
        "leg_index": leg_index,
        "answers": {
            "Q_terminator": answer("present", record["terminator"]),
            "Q1_fix_ident": q1_fix_answer(record),
            "Q2_altitude_constraint": q2_altitude_answer(record),
            "Q3_turn": q3_turn_answer(record),
            "Q4_course_or_radial": q4_course_answer(record),
            "Q5_hold_params": q5_hold_answer(record),
        },
    }


def answer_display(answer_obj):
    if answer_obj["status"] != "present":
        return answer_obj["status"]
    value = answer_obj["value"]
    if isinstance(value, dict):
        if {"desc", "altitude_ft", "altitude_2_ft"} <= set(value):
            return f'{value["desc"]} {value["altitude_ft"]} ft'
        return ", ".join(f"{key}={val}" for key, val in value.items())
    return str(value)


def target_fields_from_answers(answers):
    return [
        {
            "field_name": field_name,
            "expected_value": answer_display(answer_obj),
            "expected_answer": answer_obj,
            "evidence_hint": f"Canonical PR #28 field {field_name}; verify chart evidence for this leg.",
        }
        for field_name, answer_obj in answers.items()
    ]


def safe_filename(value):
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value))


def local_pdf_path(pdf_name):
    if not pdf_name:
        return None
    for folder in [PDF_ROOT, V2604 / "pdfs"]:
        candidate = folder / pdf_name
        if candidate.exists():
            return candidate
        upper_candidate = folder / pdf_name.upper()
        if upper_candidate.exists():
            return upper_candidate
    return None


def official_pdf_url(item, pdf_name):
    if item.get("pdf_url"):
        return item["pdf_url"]
    if pdf_name:
        return f"https://aeronav.faa.gov/d-tpp/2604/{pdf_name}"
    return ""


def ensure_pdf(item, pdf_name):
    local = local_pdf_path(pdf_name)
    if local:
        return local, "local_existing"

    url = official_pdf_url(item, pdf_name)
    if not url:
        return None, "missing_no_url"

    FAA_PDF_CACHE.mkdir(parents=True, exist_ok=True)
    destination = FAA_PDF_CACHE / pdf_name
    if destination.exists():
        return destination, "faa_official_cache"

    try:
        print(f"Downloading FAA PDF: {url}")
        urlretrieve(url, destination)
        return destination, "faa_official_download"
    except (OSError, URLError) as error:
        if destination.exists():
            destination.unlink()
        return None, f"download_failed: {error}"


def bbox(x_center, y_center, width, height):
    return {
        "x_center": round(x_center, 4),
        "y_center": round(y_center, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def image_dimensions(path):
    from PIL import Image
    with Image.open(path) as img:
        return {"width": img.width, "height": img.height}


def render_pdf_first_page(pdf_path, image_path):
    image_path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as doc:
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pix.save(str(image_path))


def choose_formal_samples():
    candidates = read_json(CANDIDATE_POOL)
    sample100 = read_json(SAMPLE_100)
    candidate_by_id = {item["id"]: item for item in candidates}
    existing_ids = {item["id"] for item in sample100}

    formal = []
    airport_counts = {}
    for item in sample100:
        full = {**candidate_by_id.get(item["id"], {}), **item}
        full["id"] = item["id"]
        full["sample_source"] = "v2604_existing_100"
        formal.append(full)
        airport_counts[full["airport"]] = airport_counts.get(full["airport"], 0) + 1

    add_candidates = [
        item for item in candidates
        if item.get("kind") == "RNAV"
        and item.get("ma_leg_count", 0) >= 1
        and item["id"] not in existing_ids
        and item.get("pdf_name")
    ]
    add_candidates.sort(key=lambda item: (
        0 if local_pdf_path(item.get("pdf_name")) else 1,
        -int(item.get("ma_leg_count", 0)),
        str(item.get("airport", "")),
        str(item.get("id", "")),
    ))

    selected_add = []
    cap = 3
    for item in add_candidates:
        if len(selected_add) >= 200:
            break
        if airport_counts.get(item["airport"], 0) >= cap:
            continue
        selected_add.append({**item, "sample_source": "issue19_rnav_expansion_200"})
        airport_counts[item["airport"]] = airport_counts.get(item["airport"], 0) + 1

    if len(selected_add) < 200:
        selected_ids = {item["id"] for item in selected_add}
        for item in add_candidates:
            if len(selected_add) >= 200:
                break
            if item["id"] in selected_ids:
                continue
            selected_add.append({**item, "sample_source": "issue19_rnav_expansion_200_cap_relaxed"})

    if len(selected_add) != 200:
        raise RuntimeError(f"Could not select 200 RNAV add-on charts; got {len(selected_add)}")

    formal.extend(selected_add)
    rng = random.Random(2604)
    order = list(range(len(formal)))
    rng.shuffle(order)
    split_by_index = {}
    for pos, index in enumerate(order):
        split_by_index[index] = "development" if pos < 200 else "evaluation" if pos < 275 else "probe"
    for index, item in enumerate(formal):
        item["dataset_split"] = split_by_index[index]
    return formal


def materialize_dataset(dataset_name, selected, source_kind):
    dataset_root = ROOT / "datasets" / dataset_name
    image_root = dataset_root / "images"
    pdf_copy_root = dataset_root / "pdfs"
    canonical_dir = dataset_root / "targets/canonical_proxy_gt"
    prelabel_dir = dataset_root / "prelabels"
    annotations_root = dataset_root / "annotations"

    for folder in [
        image_root,
        pdf_copy_root,
        canonical_dir,
        prelabel_dir,
        annotations_root / "by_annotator",
        annotations_root / "submissions",
        dataset_root / "manifests",
        dataset_root / "targets",
        dataset_root / "reports",
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    raw_by_proc = load_raw_index()
    manifest = []
    combined_canonical = []
    targets = []
    leg_index = {}
    warnings = []

    for seq, item in enumerate(selected, start=1):
        chart_id = item["id"]
        safe_chart = safe_filename(chart_id)
        pdf_name = item.get("pdf_name") or f'{Path(item.get("image", "")).stem.replace("_p0", "")}.PDF'
        if source_kind == "practice" and item.get("image_path") and not item.get("pdf_name"):
            pdf_path, pdf_source = None, "practice_image_only"
        else:
            pdf_path, pdf_source = ensure_pdf(item, pdf_name)
        image_name = f"{seq:03d}__{safe_chart}__{Path(pdf_name).stem}_p0.png"
        image_path = image_root / image_name

        existing_image = V2604 / "charts" / (item.get("image") or image_name)
        if source_kind == "practice" and item.get("image_path"):
            existing_image = Path(item["image_path"])

        if existing_image.exists():
            shutil.copy2(existing_image, image_path)
        elif pdf_path and pdf_path.exists():
            render_pdf_first_page(pdf_path, image_path)
        else:
            warnings.append({"chart_id": chart_id, "warning": f"Missing image/PDF for {pdf_name}; source={pdf_source}"})
            continue

        if pdf_path and pdf_path.exists():
            shutil.copy2(pdf_path, pdf_copy_root / pdf_name)

        records = raw_by_proc.get((item["airport"], item["proc_ident"]), [])
        missed_records = select_missed_records(records, item.get("ma_leg_count"), item.get("proc_ident"))
        if not missed_records:
            warnings.append({"chart_id": chart_id, "warning": "No missed-approach records selected from CIFP"})

        canonical_legs = [canonical_for_record(record, idx + 1) for idx, record in enumerate(missed_records)]
        canonical = {
            "chart_id": chart_id,
            "procedure": {
                "airport": item["airport"],
                "approach_ident": item["proc_ident"],
                "chart_name": item.get("chart_name", ""),
            },
            "missed_approach": {
                "leg_count": answer("present", len(canonical_legs)),
                "legs": canonical_legs,
            },
        }
        write_json(canonical_dir / f"{chart_id}.json", canonical)
        combined_canonical.append(canonical)

        platform_legs = []
        leg_index[chart_id] = {}
        for leg_no, (record, canonical_leg) in enumerate(zip(missed_records, canonical_legs), start=1):
            candidate_leg_id = f"{chart_id}__ma{leg_no}"
            leg_index[chart_id][candidate_leg_id] = {
                "canonical_leg_index": leg_no,
                "source_seq_no": record["seq_no"],
                "source_trans_ident": record["trans_ident"],
                "leg_type": record["terminator"],
                "canonical_proxy_gt_file": str(canonical_dir / f"{chart_id}.json").replace("\\", "/"),
                "raw_record": record["raw_record"],
            }
            platform_legs.append({
                "candidate_leg_id": candidate_leg_id,
                "canonical_leg_index": leg_no,
                "source_seq_no": record["seq_no"],
                "source_trans_ident": record["trans_ident"],
                "leg_type": record["terminator"],
                "target_fields": target_fields_from_answers(canonical_leg["answers"]),
                "review_status": "cifp424_canonical_proxy",
            })

        dims = image_dimensions(image_path)
        manifest_item = {
            "chart_id": chart_id,
            "airport": item["airport"],
            "proc_ident": item["proc_ident"],
            "chart_name": item.get("chart_name", ""),
            "kind": item.get("kind", ""),
            "holding_required": bool(item.get("holding_required", False)),
            "ma_leg_count": len(canonical_legs),
            "source_ma_leg_count": item.get("ma_leg_count"),
            "dataset_split": item.get("dataset_split", "practice"),
            "sample_source": item.get("sample_source", source_kind),
            "image_path": str(image_path).replace("\\", "/"),
            "image_file": image_name,
            "pdf_file": pdf_name if pdf_path and pdf_path.exists() else "",
            "pdf_source": pdf_source,
            "pdf_url": official_pdf_url(item, pdf_name),
            "image_dimensions": dims,
            "sample_type": "multi_leg" if len(canonical_legs) >= 4 else "holding" if item.get("holding_required") else "simple",
            "selection_reason": item.get("selection_reason", "Selected according to issue-driven 2604 dataset plan."),
            "needs_priority_review": len(canonical_legs) >= 4 or bool(item.get("holding_required")),
        }
        manifest.append(manifest_item)

        targets.append({
            "chart_id": chart_id,
            "image_path": manifest_item["image_path"],
            "sample_type": manifest_item["sample_type"],
            "dataset_split": manifest_item["dataset_split"],
            "main_transition_candidate": "R",
            "candidate_missed_approach_leg_count": len(platform_legs),
            "canonical_schema_version": "missed_approach_leg_v1_pr28",
            "canonical_proxy_gt_file": str(canonical_dir / f"{chart_id}.json").replace("\\", "/"),
            "candidate_legs": platform_legs,
            "target_use_policy": "Canonical CIFP424 proxy target. Annotation boxes should map to candidate_leg_id + leg_type + Q-field.",
        })

        present_mappings = []
        for leg in platform_legs:
            for field in leg["target_fields"]:
                if field["field_name"] == "Q_terminator" or field["expected_answer"]["status"] != "present":
                    continue
                present_mappings.append({
                    "candidate_leg_id": leg["candidate_leg_id"],
                    "canonical_leg_index": leg["canonical_leg_index"],
                    "leg_type": leg["leg_type"],
                    "field_name": field["field_name"],
                    "expected_value": field["expected_value"],
                    "expected_answer": field["expected_answer"],
                    "match_basis": "generic candidate from CIFP424 target; human must verify chart evidence or replace with fine-grained box",
                    "confidence": 0.35,
                    "human_decision": "pending",
                    "human_notes": "",
                    "canonical_proxy_gt_file": str(canonical_dir / f"{chart_id}.json").replace("\\", "/"),
                    "source_seq_no": leg["source_seq_no"],
                    "source_trans_ident": leg["source_trans_ident"],
                })

        prelabel = {
            "chart_id": chart_id,
            "image_path": manifest_item["image_path"],
            "image_dimensions": dims,
            "prelabel_version": "v0.20-shujuji-generic-coarse-candidates",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_policy": {
                "final_ground_truth": False,
                "human_calibration_required": True,
                "upper_coarse_boxes_are_formal_annotations": True,
                "lower_detail_box_is_seed_only": True,
                "candidate_mappings_are_cifp424_targets_not_independent_predictions": True,
            },
            "review_priority": "high" if manifest_item["needs_priority_review"] else "normal",
            "target_summary": {
                "candidate_missed_approach_leg_count": len(platform_legs),
                "candidate_leg_ids": [leg["candidate_leg_id"] for leg in platform_legs],
            },
            "regions": [
                {
                    "region_id": f"{chart_id}_01_missed_approach_text",
                    "region_type": "MISSED_APPROACH_TEXT",
                    "bbox": bbox(0.805, 0.142, 0.33, 0.07),
                    "ocr_text": "",
                    "label": "upper coarse formal annotation: missed-approach text block",
                    "confidence": 0.35,
                    "annotation_scope": "upper_coarse_formal_annotation",
                    "is_formal_annotation_candidate": True,
                    "candidate_mappings": present_mappings,
                    "human_review": {"review_action": "pending", "notes": ""},
                },
                {
                    "region_id": f"{chart_id}_02_plan_view",
                    "region_type": "PLAN_VIEW",
                    "bbox": bbox(0.5, 0.43, 0.94, 0.48),
                    "ocr_text": "",
                    "label": "coarse plan-view context for missed approach",
                    "confidence": 0.3,
                    "annotation_scope": "upper_coarse_formal_annotation",
                    "is_formal_annotation_candidate": True,
                    "candidate_mappings": [],
                    "human_review": {"review_action": "pending", "notes": ""},
                },
                {
                    "region_id": f"{chart_id}_03_lower_detail_area",
                    "region_type": "MISSED_APPROACH_DETAIL_AREA",
                    "bbox": bbox(0.52, 0.705, 0.42, 0.105),
                    "ocr_text": "",
                    "label": "seed lower/profile missed-approach detail area; adjust before final acceptance",
                    "confidence": 0.25,
                    "annotation_scope": "lower_detail_seed",
                    "is_formal_annotation_candidate": True,
                    "candidate_mappings": [],
                    "human_review": {"review_action": "pending", "notes": "Generic seed only; add fine-grained boxes as needed."},
                },
            ],
        }
        write_json(prelabel_dir / f"{chart_id}.json", prelabel)

    write_json(dataset_root / "manifest.json", manifest)
    write_json(dataset_root / "manifests" / f"{dataset_name}_manifest.json", manifest)
    write_json(dataset_root / "targets/canonical_proxy_gt_combined.json", combined_canonical)
    write_json(dataset_root / "targets/canonical_targets.json", targets)
    write_json(dataset_root / "targets/canonical_leg_index.json", leg_index)
    write_json(dataset_root / "reports/materialization_report.json", {
        "dataset": dataset_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": len(manifest),
        "source_kind": source_kind,
        "warnings": warnings,
        "counts_by_split": count_by(manifest, "dataset_split"),
        "counts_by_kind": count_by(manifest, "kind"),
        "counts_by_source": count_by(manifest, "sample_source"),
        "counts_by_holding": count_by(manifest, "holding_required"),
    })
    return manifest


def count_by(items, key):
    result = {}
    for item in items:
        value = str(item.get(key, ""))
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def materialize_practice10():
    src_manifest = read_json(PRACTICE_SRC_MANIFEST)
    selected = []
    for index, item in enumerate(src_manifest, start=1):
        selected.append({
            "id": item["chart_id"],
            "airport": item["airport"],
            "proc_ident": item["proc_ident"],
            "chart_name": item["chart_name"],
            "kind": "PILOT",
            "holding_required": item.get("sample_type") in {"holding", "multi_leg", "anomaly"},
            "ma_leg_count": 1,
            "dataset_split": "practice",
            "sample_source": "practice10_not_final",
            "image_path": item["image_path"],
            "selection_reason": item.get("selection_reason", "Practice sample"),
        })
    manifest = materialize_dataset("practice10", selected, "practice")

    target_src = read_json(PRACTICE_SRC_TARGETS / "pilot_canonical_targets_10.json")
    canonical_src_dir = PRACTICE_SRC_TARGETS / "canonical_proxy_gt_10"
    dataset_root = ROOT / "datasets/practice10"
    write_json(dataset_root / "targets/canonical_targets.json", [
        {
            **target,
            "image_path": next((item["image_path"] for item in manifest if item["chart_id"] == target["chart_id"]), target.get("image_path", "")),
            "dataset_split": "practice",
        }
        for target in target_src
    ])
    combined = []
    for item in manifest:
        src = canonical_src_dir / f'{item["chart_id"]}.json'
        if src.exists():
            canonical = read_json(src)
            combined.append(canonical)
            write_json(dataset_root / "targets/canonical_proxy_gt" / f'{item["chart_id"]}.json', canonical)
    write_json(dataset_root / "targets/canonical_proxy_gt_combined.json", combined)

    for item in manifest:
        src = PRACTICE_SRC_PRELABELS / f'{item["chart_id"]}.json'
        if src.exists():
            prelabel = read_json(src)
            prelabel["image_path"] = item["image_path"]
            prelabel["practice_only"] = True
            write_json(dataset_root / "prelabels" / f'{item["chart_id"]}.json', prelabel)
    return manifest


def write_docs(formal_manifest, practice_manifest):
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    write_json(ROOT / "dataset_index.json", {
        "practice10": {
            "url_path": "/practice/",
            "count": len(practice_manifest),
            "final_dataset": False,
            "annotation_save_policy": "practice annotations are saved separately and excluded from final formal300 exports",
        },
        "formal300": {
            "url_path": "/formal/",
            "count": len(formal_manifest),
            "final_dataset": True,
            "splits": count_by(formal_manifest, "dataset_split"),
            "annotation_save_policy": "formal annotations are saved by annotator and timestamp to support LAN multi-person work",
        },
    })
    (docs / "多人协同标注说明.md").write_text(
        """# 多人协同标注说明

## 启动方式

在服务器/主机电脑上双击 `tools\\shujuji_annotation\\启动标注平台.bat`，或在 PowerShell 中运行：

```powershell
cd tools\\shujuji_annotation\\annotation_platform
node server.js
```

服务默认监听 `0.0.0.0:8787`，局域网同学访问主机 IP 即可。

## 两个入口

- 练习入口：`http://主机IP:8787/practice/`
- 正式入口：`http://主机IP:8787/formal/`

练习入口只用于熟悉流程，保存到 practice10 专用目录，不进入正式统计。

正式入口用于 300 张数据集人工校准。每个人必须先在右上角填写自己的标注人名字，再开始保存。

## 多人分工/避免重复

正式入口按“领取航图”工作，不建议多人标同一张图。

- 填写标注人后，左侧列表会显示每张图的领取状态。
- 点击一张未领取航图时，服务器会自动把它登记到你的名下。
- 其他人再打开这张图会被阻止，避免重复标注。
- 如果有人误领，需要负责人手动检查 `tools\\shujuji_annotation\\datasets\\formal300\\annotations\\claims.json` 后再调整。

## 正式保存位置

正式标注会同时保存两份：

- 每人当前最新版：`tools\\shujuji_annotation\\datasets\\formal300\\annotations\\by_annotator\\<标注人>\\<chart_id>.json`
- 每次提交快照：`tools\\shujuji_annotation\\datasets\\formal300\\annotations\\submissions\\<chart_id>\\<时间戳>__<标注人>.json`

这样多人同时访问时，不会互相覆盖。后续汇总时按标注人或按 chart_id 收集即可。

## 标注要求

- 上方复飞文字、平面图、下方复飞细节区域可用大框。
- 下方复飞细节中的高度、箭头、fix/navaid、heading/radial/track、holding、DME/距离等，应尽量小框精标。
- accepted 映射必须说清：第几个航段、航段类型、PR #28 最大 JSON 的哪个字段。
- 页面中的 PR #28 对齐是人工证据覆盖/证据对齐，不是独立模型正确率。
""",
        encoding="utf-8",
    )
    (ROOT / "README.md").write_text(
        """# tools\\shujuji_annotation 数据集标注工作区

本目录用于 FAA missed approach 多人协同人工校准。

## 目录

- `datasets/practice10`：10 张练习航图，不进入最终结果。
- `datasets/formal300`：300 张正式航图，按 issue 要求从 2604 cycle 数据中建立。
- `annotation_platform`：多人局域网标注网页。
- `scripts`：数据集构建脚本。
- `docs`：启动、保存和协同说明。
- `docs/数据集与目录结构说明.md`：300 张选择规则、PR #28 JSON 对应关系、多人领取规则。
- `docs/多人协同标注说明.md`：局域网启动、正式保存位置、标注要求。

## 入口

启动 `启动标注平台.bat` 后访问：

- 练习：`http://主机IP:8787/practice/`
- 正式：`http://主机IP:8787/formal/`

正式入口按“领取航图”防重复：每个人填写标注人后领取不同航图，不建议多人标同一张图。
""",
        encoding="utf-8",
    )
    (ROOT / "启动标注平台.bat").write_text(
        '@echo off\r\ncd /d "%~dp0annotation_platform"\r\nnode server.js\r\npause\r\n',
        encoding="utf-8",
    )


def main():
    (ROOT / "config").mkdir(parents=True, exist_ok=True)
    max_set_src = ROOT / "config/max_set_from_FAACIFP18.v1.json"
    if not max_set_src.exists():
        max_set_src.parent.mkdir(parents=True, exist_ok=True)
        max_set_src.write_text("{}\n", encoding="utf-8")

    practice_manifest = materialize_practice10()
    formal_selected = choose_formal_samples()
    formal_manifest = materialize_dataset("formal300", formal_selected, "formal")
    write_docs(formal_manifest, practice_manifest)
    print(f"practice10: {len(practice_manifest)} charts")
    print(f"formal300: {len(formal_manifest)} charts")
    print(f"formal splits: {count_by(formal_manifest, 'dataset_split')}")
    print(f"formal kinds: {count_by(formal_manifest, 'kind')}")


if __name__ == "__main__":
    main()
