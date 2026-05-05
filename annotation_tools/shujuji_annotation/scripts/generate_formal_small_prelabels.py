import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "datasets/formal300"
PRACTICE_PRELABELS = ROOT / "datasets/practice10/prelabels"

COARSE_TYPES = {"MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"}
CLIMB_TYPES = {"CA", "VA", "VD", "VI", "VM", "VR"}
FIX_SYMBOL_TYPES = {"DF", "TF", "CF", "HM", "HF", "HA"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def answer_display(answer_obj):
    status = answer_obj.get("status")
    value = answer_obj.get("value")
    if status != "present":
        return status or "unknown"
    if isinstance(value, dict):
        if {"desc", "altitude_ft", "altitude_2_ft"} <= set(value):
            return f'{value["desc"]} {value["altitude_ft"]} ft'
        return ", ".join(f"{key}={val}" for key, val in value.items())
    return str(value)


def safe_answer_value(answer_obj, key, fallback=None):
    value = answer_obj.get("value")
    if isinstance(value, dict):
        return value.get(key, fallback)
    return fallback


def present_field_lookup(target):
    lookup = {}
    for leg in target.get("candidate_legs", []):
        leg_index = int(leg.get("canonical_leg_index") or 0)
        for field in leg.get("target_fields", []):
            answer = field.get("expected_answer") or {}
            if answer.get("status") != "present":
                continue
            lookup[(leg_index, field.get("field_name"))] = {
                "candidate_leg_id": leg.get("candidate_leg_id", ""),
                "canonical_leg_index": leg_index,
                "leg_type": leg.get("leg_type", ""),
                "field_name": field.get("field_name", ""),
                "expected_value": field.get("expected_value", answer_display(answer)),
                "expected_answer": answer,
                "source_seq_no": leg.get("source_seq_no", ""),
                "source_trans_ident": leg.get("source_trans_ident", ""),
                "canonical_proxy_gt_file": target.get("canonical_proxy_gt_file", ""),
            }
    return lookup


def mapping_from_meta(meta, basis, confidence=0.28):
    return {
        "candidate_leg_id": meta["candidate_leg_id"],
        "canonical_leg_index": meta["canonical_leg_index"],
        "leg_type": meta["leg_type"],
        "field_name": meta["field_name"],
        "expected_value": meta["expected_value"],
        "expected_answer": meta["expected_answer"],
        "match_basis": basis,
        "confidence": confidence,
        "human_decision": "pending",
        "human_notes": "",
        "canonical_proxy_gt_file": meta["canonical_proxy_gt_file"],
        "source_seq_no": meta.get("source_seq_no", ""),
        "source_trans_ident": meta.get("source_trans_ident", ""),
    }


def bbox(cx, cy, width, height):
    return {
        "x_center": round(max(0.01, min(0.99, cx)), 4),
        "y_center": round(max(0.01, min(0.99, cy)), 4),
        "width": round(max(0.006, min(0.35, width)), 4),
        "height": round(max(0.006, min(0.18, height)), 4),
    }


def region(chart_id, serial, region_type, box, label, mappings, confidence=0.28):
    return {
        "region_id": f"{chart_id}_auto_{serial:03d}_{region_type.lower()}",
        "region_type": region_type,
        "bbox": box,
        "ocr_text": "",
        "label": label,
        "confidence": confidence,
        "annotation_scope": "lower_detail_prelabel_candidate",
        "is_formal_annotation_candidate": True,
        "candidate_mappings": mappings,
        "needs_human_decision": True,
        "human_review": {
            "review_action": "pending",
            "notes": "Auto small-box prelabel candidate for formal300. Human must verify/adjust before acceptance.",
        },
    }


def lower_roi(prelabel):
    for item in prelabel.get("regions", []):
        if item.get("region_type") == "MISSED_APPROACH_DETAIL_AREA":
            return item["bbox"]
    return {"x_center": 0.52, "y_center": 0.705, "width": 0.42, "height": 0.105}


def cell_layout(roi, group_count):
    group_count = max(1, group_count)
    left = roi["x_center"] - roi["width"] / 2
    top = roi["y_center"] - roi["height"] / 2
    cell_w = roi["width"] / group_count
    cells = []
    for index in range(group_count):
        cells.append({
            "left": left + cell_w * index,
            "center": left + cell_w * (index + 0.5),
            "top": top,
            "width": cell_w,
            "height": roi["height"],
        })
    return cells


def group_plan_for_target(target, lookup):
    groups = []
    for leg in target.get("candidate_legs", []):
        leg_index = int(leg.get("canonical_leg_index") or 0)
        leg_type = leg.get("leg_type", "")
        q1 = lookup.get((leg_index, "Q1_fix_ident"))
        q2 = lookup.get((leg_index, "Q2_altitude_constraint"))
        q3 = lookup.get((leg_index, "Q3_turn"))
        q4 = lookup.get((leg_index, "Q4_course_or_radial"))
        q5 = lookup.get((leg_index, "Q5_hold_params"))

        if q2 or leg_type in CLIMB_TYPES:
            groups.append({"leg_index": leg_index, "leg_type": leg_type, "role": "climb", "fields": [item for item in [q2, q4] if item]})

        if q3:
            groups.append({"leg_index": leg_index, "leg_type": leg_type, "role": "turn", "fields": [q3]})

        if q4 and isinstance(q4["expected_answer"].get("value"), dict) and q4["expected_answer"]["value"].get("type") == "navaid_radial":
            groups.append({"leg_index": leg_index, "leg_type": leg_type, "role": "radial", "fields": [q4]})
        elif q4 and not any(q4 in group.get("fields", []) for group in groups):
            groups.append({"leg_index": leg_index, "leg_type": leg_type, "role": "course", "fields": [q4]})

        if q1:
            groups.append({"leg_index": leg_index, "leg_type": leg_type, "role": "fix", "fields": [q1]})

        if q5:
            groups.append({"leg_index": leg_index, "leg_type": leg_type, "role": "hold", "fields": [q5, q1, q2] if q1 or q2 else [q5]})

    return groups or [{"leg_index": 1, "leg_type": "", "role": "unknown", "fields": []}]


def build_group_regions(chart_id, group, cell, serial):
    regions = []
    cw = cell["width"]
    ch = cell["height"]
    x = cell["center"]
    top = cell["top"]
    role = group["role"]

    def add(region_type, x_offset, y_frac, w_frac, h_frac, label, meta):
        nonlocal serial
        mappings = [mapping_from_meta(meta, f"template lower-detail {region_type} evidence from CIFP424 PR28 field", 0.28)] if meta else []
        regions.append(region(chart_id, serial, region_type, bbox(x + cw * x_offset, top + ch * y_frac, cw * w_frac, ch * h_frac), label, mappings))
        serial += 1

    q_by_field = {item["field_name"]: item for item in group.get("fields", []) if item}
    q1 = q_by_field.get("Q1_fix_ident")
    q2 = q_by_field.get("Q2_altitude_constraint")
    q3 = q_by_field.get("Q3_turn")
    q4 = q_by_field.get("Q4_course_or_radial")
    q5 = q_by_field.get("Q5_hold_params")

    if role == "climb":
        if q2:
            alt = safe_answer_value(q2["expected_answer"], "altitude_ft", q2["expected_value"])
            add("ALTITUDE_TEXT", 0.0, 0.23, 0.72, 0.18, f"altitude {alt}", q2)
            add("CLIMB_ARROW", -0.22, 0.56, 0.28, 0.58, "climb arrow", q2)
        else:
            add("CLIMB_ARROW", -0.08, 0.56, 0.28, 0.58, "climb arrow", None)
        if q4:
            add("HEADING_TEXT", 0.08, 0.82, 0.86, 0.18, f"course/heading {q4['expected_value']}", q4)

    elif role == "turn":
        add("PATH_SEGMENT", 0.0, 0.56, 0.82, 0.68, f"turn/path {q3['expected_value']}", q3)

    elif role == "radial":
        value = q4["expected_answer"].get("value") if q4 else {}
        navaid = value.get("navaid") if isinstance(value, dict) else ""
        radial = value.get("radial_deg") if isinstance(value, dict) else ""
        direction = value.get("direction") if isinstance(value, dict) else ""
        add("NAVAID_TEXT", 0.0, 0.24, 0.74, 0.18, f"navaid {navaid}", q4)
        add("RADIAL_TEXT", 0.0, 0.52, 0.82, 0.18, f"radial {radial}", q4)
        if direction:
            add("OUTBOUND_INBOUND_MARK", 0.0, 0.82, 0.82, 0.18, f"direction {direction}", q4)

    elif role == "course":
        add("TRACK_OR_RADIAL_TEXT", 0.0, 0.48, 0.82, 0.2, f"course/track {q4['expected_value']}", q4)

    elif role == "fix":
        add("FIX_TEXT", 0.0, 0.28, 0.86, 0.2, f"fix {q1['expected_value']}", q1)
        if group.get("leg_type") in FIX_SYMBOL_TYPES:
            add("FIX_SYMBOL", 0.0, 0.66, 0.44, 0.42, "fix symbol", q1)

    elif role == "hold":
        if q5:
            add("HOLDING_PATTERN", -0.08, 0.55, 0.74, 0.7, "holding pattern", q5)
            value = q5["expected_answer"].get("value") if isinstance(q5["expected_answer"], dict) else {}
            if isinstance(value, dict) and value.get("inbound_course_deg") is not None:
                add("TRACK_OR_RADIAL_TEXT", 0.18, 0.26, 0.86, 0.18, f"holding course {value.get('inbound_course_deg')}", q5)
            if isinstance(value, dict) and value.get("leg_time_min") is not None:
                add("HOLDING_TIME_TEXT", 0.18, 0.8, 0.8, 0.18, f"holding time {value.get('leg_time_min')}", q5)
            if isinstance(value, dict) and value.get("leg_distance_nm") is not None:
                add("DME_DISTANCE_TEXT", 0.18, 0.8, 0.8, 0.18, f"holding distance {value.get('leg_distance_nm')}", q5)

    return regions, serial


def covered_keys(regions):
    keys = set()
    for item in regions:
        for mapping in item.get("candidate_mappings", []):
            keys.add((int(mapping.get("canonical_leg_index") or 0), mapping.get("field_name")))
    return keys


def parse_leg_index(mapping):
    if mapping.get("canonical_leg_index"):
        return int(mapping["canonical_leg_index"])
    leg_id = mapping.get("candidate_leg_id", "")
    if "__ma" in leg_id:
        try:
            return int(leg_id.rsplit("__ma", 1)[1].split()[0])
        except ValueError:
            return 0
    return 0


def adapt_practice_regions(chart_id, target, lookup):
    source_path = PRACTICE_PRELABELS / f"{chart_id}.json"
    if not source_path.exists():
        return []
    source = read_json(source_path)
    output = []
    serial = 800
    for source_region in source.get("regions", []):
        if source_region.get("region_type") in COARSE_TYPES:
            continue
        adapted = deepcopy(source_region)
        adapted["region_id"] = f"{chart_id}_pilotcopy_{serial:03d}_{adapted.get('region_type', 'region').lower()}"
        adapted["annotation_scope"] = "lower_detail_prelabel_candidate"
        adapted["confidence"] = min(float(adapted.get("confidence") or 0.45), 0.45)
        adapted["human_review"] = {"review_action": "pending", "notes": "Copied from reviewed pilot10 small-box prelabel; verify in formal300 context."}
        mappings = []
        for old_mapping in source_region.get("candidate_mappings", []):
            leg_index = parse_leg_index(old_mapping)
            field_name = old_mapping.get("field_name")
            meta = lookup.get((leg_index, field_name))
            if meta:
                mappings.append(mapping_from_meta(meta, "copied pilot10 small-box evidence mapped to formal300 PR28 target", 0.45))
        adapted["candidate_mappings"] = mappings
        output.append(adapted)
        serial += 1
    return output


def generate_for_chart(manifest_item, target):
    chart_id = manifest_item["chart_id"]
    prelabel_path = FORMAL / "prelabels" / f"{chart_id}.json"
    prelabel = read_json(prelabel_path)
    lookup = present_field_lookup(target)
    coarse_regions = [item for item in prelabel.get("regions", []) if item.get("region_type") in COARSE_TYPES]

    fine_regions = adapt_practice_regions(chart_id, target, lookup)
    covered = covered_keys(fine_regions)
    missing_lookup = {key: meta for key, meta in lookup.items() if key[1] != "Q_terminator" and key not in covered}

    if missing_lookup:
        missing_target = deepcopy(target)
        for leg in missing_target.get("candidate_legs", []):
            leg_index = int(leg.get("canonical_leg_index") or 0)
            leg["target_fields"] = [
                field for field in leg.get("target_fields", [])
                if (leg_index, field.get("field_name")) in missing_lookup
            ]
        roi = lower_roi(prelabel)
        groups = group_plan_for_target(missing_target, missing_lookup)
        cells = cell_layout(roi, len(groups))
        serial = 1
        for group, cell in zip(groups, cells):
            generated, serial = build_group_regions(chart_id, group, cell, serial)
            fine_regions.extend(generated)

    prelabel["regions"] = coarse_regions + fine_regions
    prelabel["prelabel_version"] = "v0.21-formal300-smallbox-template-prelabels"
    prelabel["generated_at"] = datetime.now(timezone.utc).isoformat()
    prelabel.setdefault("generation_policy", {})
    prelabel["generation_policy"].update({
        "formal300_small_box_prelabels_added": True,
        "small_box_source": "pilot10 reviewed boxes when available; otherwise PR28/CIFP424-driven layout templates inside lower detail ROI",
        "small_box_final_ground_truth": False,
        "small_box_human_calibration_required": True,
        "candidate_mappings_are_cifp424_targets_not_independent_predictions": True,
    })
    write_json(prelabel_path, prelabel)
    return {
        "chart_id": chart_id,
        "region_count": len(prelabel["regions"]),
        "coarse_count": len(coarse_regions),
        "fine_count": len(fine_regions),
        "copied_from_pilot10": (PRACTICE_PRELABELS / f"{chart_id}.json").exists(),
        "present_field_count": len([key for key in lookup if key[1] != "Q_terminator"]),
        "covered_field_count": len(covered_keys(fine_regions)),
    }


def main():
    manifest = read_json(FORMAL / "manifest.json")
    targets = {item["chart_id"]: item for item in read_json(FORMAL / "targets/canonical_targets.json")}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "formal300",
        "method": "copy reviewed pilot10 small boxes when possible, then add PR28/CIFP424 layout-template small boxes for uncovered present fields",
        "final_ground_truth": False,
        "human_calibration_required": True,
        "charts": [],
    }
    for item in manifest:
        chart_id = item["chart_id"]
        report["charts"].append(generate_for_chart(item, targets[chart_id]))
    write_json(FORMAL / "reports/formal300_small_prelabels_report.json", report)

    fine_counts = [item["fine_count"] for item in report["charts"]]
    copied = sum(1 for item in report["charts"] if item["copied_from_pilot10"])
    print(f"Updated {len(report['charts'])} formal300 prelabels")
    print(f"pilot10 boxes copied for {copied} charts")
    print(f"fine boxes min/avg/max: {min(fine_counts)} / {sum(fine_counts)/len(fine_counts):.1f} / {max(fine_counts)}")


if __name__ == "__main__":
    main()
