import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import cv2
import fitz
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "datasets/formal300"
PRACTICE_PRELABELS = ROOT / "datasets/practice10/prelabels"

COARSE_TYPES = {"MISSED_APPROACH_TEXT", "PLAN_VIEW", "MISSED_APPROACH_DETAIL_AREA"}
CLIMB_TYPES = {"CA", "VA", "VD", "VI", "VM", "VR"}
FIX_SYMBOL_TYPES = {"CF", "DF", "TF", "HA", "HF", "HM"}
DEFAULT_LOWER_ROI = {"x_center": 0.52, "y_center": 0.705, "width": 0.42, "height": 0.105}
ENABLE_LOW_CONFIDENCE_FALLBACK_BOXES = False


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_workspace_path(value):
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    root_candidate = ROOT / candidate
    if root_candidate.exists():
        return root_candidate
    return Path.cwd() / candidate


def bbox(cx, cy, width, height):
    return {
        "x_center": round(max(0.005, min(0.995, cx)), 4),
        "y_center": round(max(0.005, min(0.995, cy)), 4),
        "width": round(max(0.004, min(0.35, width)), 4),
        "height": round(max(0.004, min(0.2, height)), 4),
    }


def bbox_union(boxes, pad_x=0.0, pad_y=0.0):
    if not boxes:
        return None
    left = min(box["x_center"] - box["width"] / 2 for box in boxes) - pad_x
    top = min(box["y_center"] - box["height"] / 2 for box in boxes) - pad_y
    right = max(box["x_center"] + box["width"] / 2 for box in boxes) + pad_x
    bottom = max(box["y_center"] + box["height"] / 2 for box in boxes) + pad_y
    return bbox((left + right) / 2, (top + bottom) / 2, right - left, bottom - top)


def norm_text(text):
    text = str(text or "").upper()
    text = text.replace("ЁУ", "").replace("°", "").replace("º", "")
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"[^A-Z0-9.-]", "", text)


def angle_tokens(value):
    if value is None:
        return []
    rounded = int(round(float(value))) % 360
    return [f"{rounded:03d}", str(rounded)]


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


def mapping(meta, basis, confidence=0.55):
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


def region(chart_id, serial, region_type, box, label, mappings, confidence=0.55, source="pdf_text_or_icon_detection"):
    return {
        "region_id": f"{chart_id}_iconalign_{serial:03d}_{region_type.lower()}",
        "region_type": region_type,
        "bbox": box,
        "ocr_text": "",
        "label": label,
        "confidence": confidence,
        "source_layer": source,
        "annotation_scope": "lower_detail_icon_aligned_prelabel_candidate",
        "is_formal_annotation_candidate": True,
        "candidate_mappings": mappings,
        "needs_human_decision": True,
        "human_review": {
            "review_action": "pending",
            "notes": "Icon/text-aligned auto prelabel. Human must verify/adjust before acceptance.",
        },
    }


def target_lookup(target):
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
                "expected_value": field.get("expected_value") or answer_display(answer),
                "expected_answer": answer,
                "source_seq_no": leg.get("source_seq_no", ""),
                "source_trans_ident": leg.get("source_trans_ident", ""),
                "canonical_proxy_gt_file": target.get("canonical_proxy_gt_file", ""),
            }
    return lookup


def is_navaid_radial_meta(meta):
    if not meta:
        return False
    value = (meta.get("expected_answer") or {}).get("value")
    return meta.get("field_name") == "Q4_course_or_radial" and isinstance(value, dict) and value.get("type") == "navaid_radial"


def pdf_words(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    width = float(page.rect.width)
    height = float(page.rect.height)
    output = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        box = bbox((x0 + x1) / (2 * width), (y0 + y1) / (2 * height), (x1 - x0) / width, (y1 - y0) / height)
        output.append({"text": text, "norm": norm_text(text), "bbox": box})
    return output


def lower_words(words):
    return [
        item for item in words
        if 0.55 <= item["bbox"]["y_center"] <= 0.84
        and 0.04 <= item["bbox"]["x_center"] <= 0.92
        and item["norm"]
    ]


def tokens_for_meta(meta):
    field = meta["field_name"]
    answer = meta["expected_answer"]
    value = answer.get("value")
    tokens = []
    if field == "Q1_fix_ident" and isinstance(value, str):
        tokens.append(norm_text(value))
    elif field == "Q2_altitude_constraint" and isinstance(value, dict):
        if value.get("altitude_ft") is not None:
            tokens.append(str(int(value["altitude_ft"])))
        if value.get("altitude_2_ft") is not None:
            tokens.append(str(int(value["altitude_2_ft"])))
    elif field == "Q4_course_or_radial" and isinstance(value, dict):
        if value.get("type") == "navaid_radial":
            if value.get("navaid"):
                tokens.append(norm_text(value["navaid"]))
            if value.get("radial_deg") is not None:
                rounded = int(round(float(value["radial_deg"]))) % 360
                tokens.extend([f"R-{rounded:03d}", f"R{rounded:03d}", f"{rounded:03d}"])
            if value.get("direction"):
                direction = str(value["direction"]).upper()
                tokens.append("INBND" if direction.startswith("IN") else "OUTBND")
        elif value.get("course_deg") is not None:
            tokens.extend(angle_tokens(value["course_deg"]))
    elif field == "Q5_hold_params" and isinstance(value, dict):
        tokens.extend(angle_tokens(value.get("inbound_course_deg")))
        if value.get("leg_distance_nm") is not None:
            tokens.append(str(int(round(float(value["leg_distance_nm"])))))
        if value.get("leg_time_min") is not None:
            tokens.extend(["1", "1MIN", "MIN"])
    return [token for token in dict.fromkeys(tokens) if token]


def word_matches(words, lookup):
    matches = []
    for key, meta in lookup.items():
        if meta["field_name"] == "Q_terminator":
            continue
        expected_tokens = tokens_for_meta(meta)
        for word in lower_words(words):
            if word["norm"] in expected_tokens:
                matches.append({"key": key, "meta": meta, "word": word})
    return matches


def detail_table_score(image_path, roi):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return 0.0
    image_height, image_width = image.shape[:2]
    x0, y0, x1, y1 = pixel_rect_from_bbox(roi, image_width, image_height)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return 0.0

    dark = cv2.threshold(crop, 125, 255, cv2.THRESH_BINARY_INV)[1]
    crop_h, crop_w = crop.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, crop_w // 5), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, crop_h // 3)))
    horizontal = cv2.morphologyEx(dark, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(dark, cv2.MORPH_OPEN, vertical_kernel)

    horizontal_rows = int(np.count_nonzero(np.count_nonzero(horizontal, axis=1) > crop_w * 0.22))
    vertical_cols = int(np.count_nonzero(np.count_nonzero(vertical, axis=0) > crop_h * 0.30))
    line_pixels = (np.count_nonzero(horizontal) + np.count_nonzero(vertical)) / max(crop_w * crop_h, 1)

    # The lower missed-approach strip is normally a compact row of boxed cells.
    # Profile-view text can match the same CIFP numbers, but it rarely has this grid signature.
    return min(horizontal_rows, 5) * 1.8 + min(vertical_cols, 12) * 1.1 + min(line_pixels * 18, 6.0)


def match_field_counts(group):
    fields = {}
    tokens = set()
    for item in group:
        fields.setdefault(item["meta"]["field_name"], set()).add(item["key"])
        tokens.add(item["word"]["norm"])
    return fields, tokens


def choose_detail_roi(prelabel, matches, image_path=None):
    base_roi = next((item["bbox"] for item in prelabel.get("regions", []) if item.get("region_type") == "MISSED_APPROACH_DETAIL_AREA"), None)
    if not matches:
        return base_roi or DEFAULT_LOWER_ROI, []

    best = []
    for anchor in matches:
        ax = anchor["word"]["bbox"]["x_center"]
        ay = anchor["word"]["bbox"]["y_center"]
        group = [
            item for item in matches
            if abs(item["word"]["bbox"]["y_center"] - ay) <= 0.028
            and abs(item["word"]["bbox"]["x_center"] - ax) <= 0.30
        ]
        distinct = {(item["key"], item["word"]["norm"]) for item in group}
        if not group:
            continue
        xs = [item["word"]["bbox"]["x_center"] for item in group]
        ys = [item["word"]["bbox"]["y_center"] for item in group]
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        text_roi = bbox_union([item["word"]["bbox"] for item in group], pad_x=0.038, pad_y=0.04)
        table_score = detail_table_score(image_path, text_roi) if image_path and text_roi else 0.0
        field_counts, token_set = match_field_counts(group)
        altitude_keys = field_counts.get("Q2_altitude_constraint", set())
        fix_keys = field_counts.get("Q1_fix_ident", set())
        course_keys = field_counts.get("Q4_course_or_radial", set())
        hold_keys = field_counts.get("Q5_hold_params", set())
        altitude_token_bonus = 5 if len({item["word"]["norm"] for item in group if item["meta"]["field_name"] == "Q2_altitude_constraint"}) >= 2 else 0
        detail_strip_bonus = 18 if table_score >= 5.0 and altitude_keys else 0
        profile_duplicate_penalty = 16 if table_score < 2.0 and (course_keys or hold_keys) and not fix_keys else 0
        left_profile_penalty = max(0.0, 0.28 - text_roi["x_center"]) * 70 if text_roi and not fix_keys else 0.0
        score = (
            len(distinct) * 8
            + len(altitude_keys) * 10
            + len(fix_keys) * 7
            + len(course_keys) * 3
            + len(hold_keys) * 2
            + altitude_token_bonus
            + detail_strip_bonus
            + table_score * 4
            - profile_duplicate_penalty
            - left_profile_penalty
            - abs(ay - 0.66) * 8
            - span_x * 4
            - span_y * 22
        )
        if not best or score > best[0]:
            best = [score, group]
    selected = best[1] if best else matches
    text_roi = bbox_union([item["word"]["bbox"] for item in selected], pad_x=0.038, pad_y=0.04)
    if not text_roi:
        return base_roi or DEFAULT_LOWER_ROI, selected
    return text_roi, selected


def in_roi(word, roi, pad=0.01):
    box = word["bbox"]
    return (
        roi["x_center"] - roi["width"] / 2 - pad <= box["x_center"] <= roi["x_center"] + roi["width"] / 2 + pad
        and roi["y_center"] - roi["height"] / 2 - pad <= box["y_center"] <= roi["y_center"] + roi["height"] / 2 + pad
    )


def text_region_type(meta, word_norm):
    field = meta["field_name"]
    value = meta["expected_answer"].get("value")
    if field == "Q1_fix_ident":
        return "FIX_TEXT"
    if field == "Q2_altitude_constraint":
        return "ALTITUDE_TEXT"
    if field == "Q4_course_or_radial":
        if isinstance(value, dict) and value.get("type") == "navaid_radial":
            if word_norm.startswith("R") or re.fullmatch(r"\d{3}", word_norm):
                return "RADIAL_TEXT"
            if word_norm in {"INBND", "OUTBND"}:
                return "OUTBOUND_INBOUND_MARK"
            return "NAVAID_TEXT"
        return "HEADING_TEXT" if meta.get("leg_type") in CLIMB_TYPES else "TRACK_OR_RADIAL_TEXT"
    if field == "Q5_hold_params":
        if word_norm in {"1", "1MIN", "MIN"}:
            return "HOLDING_TIME_TEXT"
        if re.fullmatch(r"\d+", word_norm):
            return "DME_DISTANCE_TEXT" if int(word_norm) <= 20 else "TRACK_OR_RADIAL_TEXT"
        return "TRACK_OR_RADIAL_TEXT"
    return "FIX_TEXT"


def covered_keys(regions):
    keys = set()
    for item in regions:
        for item_mapping in item.get("candidate_mappings", []):
            keys.add((int(item_mapping.get("canonical_leg_index") or 0), item_mapping.get("field_name")))
    return keys


def covered_region_type_keys(regions):
    keys = set()
    for item in regions:
        region_type = item.get("region_type", "")
        for item_mapping in item.get("candidate_mappings", []):
            keys.add((int(item_mapping.get("canonical_leg_index") or 0), item_mapping.get("field_name"), region_type))
    return keys


def parse_leg_index(item_mapping):
    if item_mapping.get("canonical_leg_index"):
        return int(item_mapping["canonical_leg_index"])
    leg_id = item_mapping.get("candidate_leg_id", "")
    if "__ma" in leg_id:
        try:
            return int(leg_id.rsplit("__ma", 1)[1].split()[0])
        except ValueError:
            return 0
    return 0


def adapt_pilot_regions(chart_id, lookup):
    source_path = PRACTICE_PRELABELS / f"{chart_id}.json"
    if not source_path.exists():
        return []
    source = read_json(source_path)
    output = []
    serial = 700
    for source_region in source.get("regions", []):
        if source_region.get("region_type") in COARSE_TYPES:
            continue
        copied = deepcopy(source_region)
        copied["region_id"] = f"{chart_id}_pilotcopy_{serial:03d}_{copied.get('region_type', 'region').lower()}"
        copied["source_layer"] = "copied_from_reviewed_pilot10_prelabel"
        copied["annotation_scope"] = "lower_detail_icon_aligned_prelabel_candidate"
        copied["confidence"] = min(float(copied.get("confidence") or 0.5), 0.55)
        copied["human_review"] = {"review_action": "pending", "notes": "Copied from reviewed pilot10 small-box prelabel; verify in formal300 context."}
        mappings = []
        for old_mapping in source_region.get("candidate_mappings", []):
            meta = lookup.get((parse_leg_index(old_mapping), old_mapping.get("field_name")))
            if not meta and copied.get("region_type") == "HEADING_TEXT":
                q4_meta = lookup.get((parse_leg_index(old_mapping), "Q4_course_or_radial"))
                q4_value = (q4_meta or {}).get("expected_answer", {}).get("value")
                if isinstance(q4_value, dict) and q4_value.get("type") == "course_deg":
                    meta = q4_meta
            if meta:
                mappings.append(mapping(meta, "copied reviewed pilot10 small box mapped to formal300 PR28 target", 0.55))
                if copied.get("region_type") == "HEADING_TEXT" and meta["field_name"] == "Q4_course_or_radial":
                    copied["source_field_name"] = "Q4_course_or_radial"
        copied["candidate_mappings"] = mappings
        output.append(copied)
        serial += 1
    return output


def pixel_rect_from_bbox(box, image_width, image_height):
    x0 = int((box["x_center"] - box["width"] / 2) * image_width)
    y0 = int((box["y_center"] - box["height"] / 2) * image_height)
    x1 = int((box["x_center"] + box["width"] / 2) * image_width)
    y1 = int((box["y_center"] + box["height"] / 2) * image_height)
    return max(0, x0), max(0, y0), min(image_width, x1), min(image_height, y1)


def bbox_from_pixels(x, y, w, h, image_width, image_height):
    return bbox((x + w / 2) / image_width, (y + h / 2) / image_height, w / image_width, h / image_height)


def detect_symbol_components(image_path, roi):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []
    image_height, image_width = image.shape[:2]
    x0, y0, x1, y1 = pixel_rect_from_bbox(roi, image_width, image_height)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return []
    dark = cv2.threshold(crop, 110, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1)))
    vertical = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 28)))
    line_mask = cv2.bitwise_or(horizontal, vertical)
    cleaned = cv2.bitwise_and(dark, cv2.bitwise_not(line_mask))
    joined = cv2.dilate(cleaned, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
    count, _, stats, _ = cv2.connectedComponentsWithStats(joined, 8)
    components = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if area < 20 or w < 4 or h < 4:
            continue
        if w > (x1 - x0) * 0.45 or h > (y1 - y0) * 0.95:
            continue
        components.append({
            "bbox": bbox_from_pixels(x0 + x, y0 + y, w, h, image_width, image_height),
            "pixel": (x0 + x, y0 + y, w, h),
            "area": int(area),
            "aspect": h / max(w, 1),
        })
    return components


def nearest_component(components, anchor_box, predicate):
    candidates = [item for item in components if predicate(item)]
    if not candidates:
        return None
    ax = anchor_box["x_center"]
    ay = anchor_box["y_center"]
    return min(candidates, key=lambda item: abs(item["bbox"]["x_center"] - ax) * 1.4 + abs(item["bbox"]["y_center"] - ay))


def choose_best_word(meta, rtype, candidates, cluster_center):
    if len(candidates) == 1:
        return candidates[0]
    value = meta["expected_answer"].get("value")
    direction_anchor = None
    if isinstance(value, dict) and value.get("direction"):
        wanted = "INBND" if str(value["direction"]).upper().startswith("IN") else "OUTBND"
        direction_matches = [item for item in candidates if item["word"]["norm"] == wanted]
        if direction_matches:
            direction_anchor = direction_matches[0]["word"]["bbox"]
    if direction_anchor and rtype in {"NAVAID_TEXT", "RADIAL_TEXT"}:
        return min(
            candidates,
            key=lambda item: abs(item["word"]["bbox"]["x_center"] - direction_anchor["x_center"]) + abs(item["word"]["bbox"]["y_center"] - direction_anchor["y_center"]) * 1.5,
        )
    cx, cy = cluster_center
    return min(
        candidates,
        key=lambda item: abs(item["word"]["bbox"]["x_center"] - cx) * 1.1 + abs(item["word"]["bbox"]["y_center"] - cy),
    )


def add_text_boxes(chart_id, serial, selected_matches, lookup, detail_roi, existing_regions):
    output = []
    already_covered = covered_region_type_keys(existing_regions)
    eligible = []
    for item in selected_matches:
        rtype = text_region_type(item["meta"], item["word"]["norm"])
        if (item["key"][0], item["key"][1], rtype) in already_covered:
            continue
        if not in_roi(item["word"], detail_roi, pad=0.02):
            continue
        eligible.append(item)
    if not eligible:
        return output, serial
    cluster_center = (
        sum(item["word"]["bbox"]["x_center"] for item in eligible) / len(eligible),
        sum(item["word"]["bbox"]["y_center"] for item in eligible) / len(eligible),
    )
    grouped = {}
    for item in eligible:
        rtype = text_region_type(item["meta"], item["word"]["norm"])
        grouped.setdefault((item["key"], rtype), []).append(item)

    for (key, rtype), candidates in sorted(grouped.items(), key=lambda entry: (entry[0][0][0], entry[0][0][1], entry[0][1])):
        meta = lookup.get(key)
        if not meta:
            continue
        item = choose_best_word(meta, rtype, candidates, cluster_center)
        word = item["word"]
        label = f"{rtype}: {word['text']} -> {meta['expected_value']}"
        output.append(region(
            chart_id,
            serial,
            rtype,
            bbox(word["bbox"]["x_center"], word["bbox"]["y_center"], word["bbox"]["width"] * 1.12, word["bbox"]["height"] * 1.25),
            label,
            [mapping(meta, f"PDF text token '{word['text']}' inside detected lower missed-approach/icon area", 0.62)],
            confidence=0.62,
            source="pdf_text_inside_detected_icon_area",
        ))
        serial += 1
    return output, serial


def add_symbol_boxes(chart_id, serial, image_path, detail_roi, lookup, text_regions):
    components = detect_symbol_components(image_path, detail_roi)
    output = []
    text_by_key = {}
    for item in text_regions:
        for item_mapping in item.get("candidate_mappings", []):
            text_by_key.setdefault((int(item_mapping["canonical_leg_index"]), item_mapping["field_name"]), []).append(item)

    for key, meta in lookup.items():
        leg_type = meta.get("leg_type", "")
        field = meta["field_name"]
        anchors = text_by_key.get(key, [])
        anchor = anchors[0]["bbox"] if anchors else detail_roi
        if field == "Q2_altitude_constraint":
            comp = nearest_component(
                components,
                anchor,
                lambda item: item["aspect"] > 1.65 and item["bbox"]["height"] > 0.009 and item["bbox"]["width"] < 0.025 and item["bbox"]["y_center"] >= anchor["y_center"] - 0.01,
            )
            if comp:
                output.append(region(chart_id, serial, "CLIMB_ARROW", comp["bbox"], f"climb arrow for {meta['expected_value']}", [mapping(meta, "detected climb/missed-approach icon near altitude text", 0.5)], 0.5, "cv_icon_component"))
                serial += 1
        if field == "Q1_fix_ident" and leg_type in FIX_SYMBOL_TYPES:
            fix_anchor = anchor
            if not anchors:
                fix_anchor = bbox(
                    detail_roi["x_center"] + detail_roi["width"] * 0.36,
                    detail_roi["y_center"] + detail_roi["height"] * 0.18,
                    detail_roi["width"] * 0.18,
                    detail_roi["height"] * 0.55,
                )
            comp = nearest_component(
                components,
                fix_anchor,
                lambda item: 0.45 <= item["aspect"] <= 2.2 and 0.008 <= item["bbox"]["width"] <= 0.04 and 0.007 <= item["bbox"]["height"] <= 0.045 and item["bbox"]["y_center"] >= fix_anchor["y_center"] - 0.04,
            )
            if comp:
                output.append(region(chart_id, serial, "FIX_SYMBOL", comp["bbox"], f"fix symbol for {meta['expected_value']}", [mapping(meta, "detected fix/navaid symbol near fix text", 0.48)], 0.48, "cv_icon_component"))
                serial += 1
        if is_navaid_radial_meta(meta):
            comp = nearest_component(
                components,
                anchor,
                lambda item: item["bbox"]["width"] > 0.022 and item["bbox"]["height"] > 0.006 and item["area"] >= 26,
            )
            if comp:
                output.append(region(chart_id, serial, "PATH_SEGMENT", comp["bbox"], f"radial/path graphic for {meta['expected_value']}", [mapping(meta, "detected radial/path graphic near navaid-radial text", 0.44)], 0.44, "cv_icon_component"))
                serial += 1
        if field in {"Q3_turn", "Q5_hold_params"}:
            comp = nearest_component(
                components,
                anchor,
                lambda item: item["bbox"]["width"] > 0.025 and item["bbox"]["height"] > 0.018,
            )
            if comp:
                rtype = "HOLDING_PATTERN" if field == "Q5_hold_params" else "PATH_SEGMENT"
                output.append(region(chart_id, serial, rtype, comp["bbox"], f"{rtype} for {meta['expected_value']}", [mapping(meta, "detected path/holding icon component inside lower missed-approach area", 0.46)], 0.46, "cv_icon_component"))
                serial += 1
    return output, serial


TEXT_LIKE_TYPES = {
    "ALTITUDE_TEXT",
    "HEADING_TEXT",
    "NAVAID_TEXT",
    "RADIAL_TEXT",
    "FIX_TEXT",
    "TRACK_OR_RADIAL_TEXT",
    "OUTBOUND_INBOUND_MARK",
    "HOLDING_TIME_TEXT",
    "DME_DISTANCE_TEXT",
}


REGION_TYPE_PRIORITY = {
    "ALTITUDE_TEXT": 1,
    "FIX_TEXT": 2,
    "NAVAID_TEXT": 3,
    "RADIAL_TEXT": 4,
    "TRACK_OR_RADIAL_TEXT": 5,
    "HEADING_TEXT": 6,
    "OUTBOUND_INBOUND_MARK": 7,
    "CLIMB_ARROW": 8,
    "FIX_SYMBOL": 9,
    "PATH_SEGMENT": 10,
    "HOLDING_PATTERN": 11,
    "HOLDING_TIME_TEXT": 12,
    "DME_DISTANCE_TEXT": 13,
}


def box_edges(box):
    return (
        box["x_center"] - box["width"] / 2,
        box["y_center"] - box["height"] / 2,
        box["x_center"] + box["width"] / 2,
        box["y_center"] + box["height"] / 2,
    )


def box_iou(a, b):
    ax0, ay0, ax1, ay1 = box_edges(a)
    bx0, by0, bx1, by1 = box_edges(b)
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return inter / max(area_a + area_b - inter, 1e-9)


def mapping_key(item_mapping):
    return (
        int(item_mapping.get("canonical_leg_index") or 0),
        item_mapping.get("field_name", ""),
        json.dumps(item_mapping.get("expected_answer"), sort_keys=True, ensure_ascii=False),
    )


def dedupe_mappings(mappings):
    seen = set()
    output = []
    for item_mapping in mappings:
        key = mapping_key(item_mapping)
        if key in seen:
            continue
        seen.add(key)
        output.append(item_mapping)
    return output


def q5_has_distance(item_mapping):
    value = (item_mapping.get("expected_answer") or {}).get("value")
    return isinstance(value, dict) and value.get("leg_distance_nm") is not None


def visible_label_text(item):
    label = str(item.get("label") or "")
    visible = " ".join(part.split("->", 1)[0] for part in label.split(";"))
    return " ".join([
        str(item.get("region_type") or ""),
        visible,
        str(item.get("ocr_text") or ""),
        str(item.get("element_role") or ""),
    ]).upper()


def has_token(item, token):
    wanted = str(token or "").strip().upper()
    if not wanted:
        return False
    return re.search(rf"(^|[^A-Z0-9]){re.escape(wanted)}([^A-Z0-9]|$)", visible_label_text(item)) is not None


def has_number(item, value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    candidates = {
        str(round(number)),
        f"{int(round(number)) % 360:03d}" if 0 <= number < 360 else "",
        "" if number.is_integer() else f"{number:.1f}".rstrip("0").rstrip("."),
        "" if number.is_integer() else str(int(number // 1)),
        "" if number.is_integer() else str(int(number // 1 + 1)),
    }
    text = visible_label_text(item)
    return any(
        candidate and re.search(rf"(^|[^0-9]){re.escape(candidate)}([^0-9]|$)", text)
        for candidate in candidates
    )


def mapping_value(item_mapping):
    return (item_mapping.get("expected_answer") or {}).get("value")


def fine_mapping_matches_visible_text(item, item_mapping):
    region_type = item.get("region_type", "")
    field_name = item_mapping.get("field_name", "")
    value = mapping_value(item_mapping)
    if region_type in COARSE_TYPES:
        return True
    if field_name == "Q_terminator":
        return False
    if item_mapping.get("leg_type") == "HM" and field_name in {"Q1_fix_ident", "Q2_altitude_constraint"}:
        # HM fix/altitude are usually inherited from the hold anchor/procedure logic, not directly
        # stated by a separate HM fine box. Leave them for runtime reasoning.
        return False
    if region_type == "ALTITUDE_TEXT":
        return field_name == "Q2_altitude_constraint" and isinstance(value, dict) and has_number(item, value.get("altitude_ft"))
    if region_type == "CLIMB_ARROW":
        return field_name == "Q2_altitude_constraint"
    if region_type == "TURN_PHRASE":
        return field_name == "Q3_turn" and has_token(item, value)
    if region_type == "FIX_TEXT":
        return field_name == "Q1_fix_ident" and has_token(item, value)
    if region_type == "FIX_SYMBOL":
        return field_name == "Q1_fix_ident"
    if region_type == "NAVAID_TEXT":
        if field_name == "Q1_fix_ident":
            return has_token(item, value)
        if field_name == "Q4_course_or_radial" and isinstance(value, dict) and value.get("type") == "navaid_radial":
            return has_token(item, value.get("navaid") or value.get("navaid_ident"))
        return False
    if region_type in {"RADIAL_TEXT", "HEADING_TEXT", "TRACK_OR_RADIAL_TEXT"}:
        if field_name == "Q4_course_or_radial" and isinstance(value, dict):
            return has_number(item, value.get("radial_deg") or value.get("course_deg"))
        if field_name == "Q5_hold_params" and isinstance(value, dict):
            return has_number(item, value.get("inbound_course_deg"))
        return False
    if region_type == "OUTBOUND_INBOUND_MARK":
        return field_name in {"Q4_course_or_radial", "Q5_hold_params"}
    if region_type == "HOLDING_TIME_TEXT":
        return field_name == "Q5_hold_params" and isinstance(value, dict) and value.get("leg_time_min") is not None
    if region_type == "DME_DISTANCE_TEXT":
        return field_name == "Q5_hold_params" and isinstance(value, dict) and value.get("leg_distance_nm") is not None and has_number(item, value.get("leg_distance_nm"))
    if region_type in {"HOLDING_PATTERN", "HOLDING_ARC", "PATH_SEGMENT", "MISSED_APPROACH_ICON", "MISSED_APPROACH_STEP_BOX"}:
        return False
    return True


def mapping_allowed_for_region_type(region_type, item_mapping):
    field_name = item_mapping.get("field_name", "")
    if field_name == "Q_terminator":
        return True
    if region_type in COARSE_TYPES:
        return True
    if region_type == "ALTITUDE_TEXT":
        return field_name == "Q2_altitude_constraint"
    if region_type == "CLIMB_ARROW":
        return field_name == "Q2_altitude_constraint"
    if region_type == "TURN_PHRASE":
        return field_name == "Q3_turn"
    if region_type in {"FIX_TEXT", "FIX_SYMBOL"}:
        return field_name == "Q1_fix_ident"
    if region_type == "NAVAID_TEXT":
        return field_name in {"Q1_fix_ident", "Q4_course_or_radial"}
    if region_type in {"RADIAL_TEXT", "HEADING_TEXT", "TRACK_OR_RADIAL_TEXT", "OUTBOUND_INBOUND_MARK"}:
        return field_name in {"Q4_course_or_radial", "Q5_hold_params"}
    if region_type in {"HOLDING_PATTERN", "HOLDING_ARC", "HOLDING_TIME_TEXT"}:
        return field_name == "Q5_hold_params"
    if region_type == "DME_DISTANCE_TEXT":
        return field_name == "Q5_hold_params" and q5_has_distance(item_mapping)
    if region_type in {"PATH_SEGMENT", "MISSED_APPROACH_ICON", "MISSED_APPROACH_STEP_BOX"}:
        return field_name in {"Q3_turn", "Q4_course_or_radial", "Q5_hold_params"}
    return True


def apply_source_hint_from_mappings(item):
    if item.get("region_type") in COARSE_TYPES:
        return item
    mappings = item.get("candidate_mappings") or []
    keys = {
        (item_mapping.get("candidate_leg_id") or "", item_mapping.get("field_name") or "")
        for item_mapping in mappings
    }
    keys.discard(("", ""))
    if len(keys) == 1:
        candidate_leg_id, field_name = next(iter(keys))
        item["source_candidate_leg_id"] = candidate_leg_id
        item["source_leg_type"] = mappings[0].get("leg_type") or ""
        item["source_field_name"] = field_name
    else:
        item.pop("source_candidate_leg_id", None)
        item.pop("source_leg_type", None)
        item.pop("source_field_name", None)
    return item


def sanitize_region_mappings(item):
    region_type = item.get("region_type", "")
    item["candidate_mappings"] = dedupe_mappings([
        item_mapping for item_mapping in item.get("candidate_mappings", [])
        if mapping_allowed_for_region_type(region_type, item_mapping)
        and fine_mapping_matches_visible_text(item, item_mapping)
    ])
    apply_source_hint_from_mappings(item)
    return item


def sanitize_region_list(regions):
    return [sanitize_region_mappings(item) for item in regions]


def leg_indices_for_region(item):
    indices = []
    for item_mapping in item.get("candidate_mappings", []):
        field_name = item_mapping.get("field_name")
        if field_name == "Q_terminator":
            continue
        leg_index = int(item_mapping.get("canonical_leg_index") or 0)
        if leg_index:
            indices.append(leg_index)
    return sorted(set(indices))


def add_mapping_if_missing(item, meta, basis, confidence):
    if not meta:
        return False
    existing = {
        (int(item_mapping.get("canonical_leg_index") or 0), item_mapping.get("field_name"))
        for item_mapping in item.get("candidate_mappings", [])
    }
    key = (int(meta.get("canonical_leg_index") or 0), meta.get("field_name"))
    if key in existing:
        return False
    item.setdefault("candidate_mappings", []).append(mapping(meta, basis, confidence))
    item["candidate_mappings"] = dedupe_mappings(item.get("candidate_mappings", []))
    return True


def add_compound_support_mappings(regions, lookup):
    for item in regions:
        region_type = item.get("region_type")
        for leg_index in leg_indices_for_region(item):
            q4 = lookup.get((leg_index, "Q4_course_or_radial"))
            if region_type in {"FIX_SYMBOL", "PATH_SEGMENT"} and is_navaid_radial_meta(q4):
                add_mapping_if_missing(
                    item,
                    q4,
                    "same-leg graphical navaid/radial evidence; include with text boxes for joint Q4 support",
                    min(0.5, max(float(item.get("confidence") or 0.4), 0.42)),
                )
            qterm = lookup.get((leg_index, "Q_terminator"))
            add_mapping_if_missing(
                item,
                qterm,
                "same-leg chart evidence preselected for joint Q_terminator support",
                min(0.55, max(float(item.get("confidence") or 0.4), 0.4)),
            )
    return regions


def merge_region_pair(base, extra):
    base["bbox"] = bbox_union([base["bbox"], extra["bbox"]]) or base["bbox"]
    base["confidence"] = max(float(base.get("confidence") or 0), float(extra.get("confidence") or 0))
    base["candidate_mappings"] = dedupe_mappings(base.get("candidate_mappings", []) + extra.get("candidate_mappings", []))
    labels = []
    for label in [base.get("label", ""), extra.get("label", "")]:
        for part in str(label or "").split(";"):
            part = part.strip()
            if part and part not in labels:
                labels.append(part)
    base["label"] = "; ".join(labels)
    if REGION_TYPE_PRIORITY.get(extra.get("region_type"), 99) < REGION_TYPE_PRIORITY.get(base.get("region_type"), 99):
        base["region_type"] = extra["region_type"]
    sanitize_region_mappings(base)
    return base


def should_merge_regions(a, b):
    iou = box_iou(a["bbox"], b["bbox"])
    if iou >= 0.72 and a.get("region_type") == b.get("region_type"):
        return True
    if iou >= 0.78 and a.get("region_type") in TEXT_LIKE_TYPES and b.get("region_type") in TEXT_LIKE_TYPES:
        return True
    if iou >= 0.82 and {a.get("region_type"), b.get("region_type")} <= {"FIX_SYMBOL", "HOLDING_PATTERN", "PATH_SEGMENT", "CLIMB_ARROW"}:
        return True
    return False


def merge_overlapping_regions(regions):
    ordered = sorted(
        regions,
        key=lambda item: (
            REGION_TYPE_PRIORITY.get(item.get("region_type"), 99),
            item["bbox"]["y_center"],
            item["bbox"]["x_center"],
            -float(item.get("confidence") or 0),
        ),
    )
    merged = []
    for item in ordered:
        target = next((existing for existing in merged if should_merge_regions(existing, item)), None)
        if target:
            merge_region_pair(target, item)
        else:
            item = deepcopy(item)
            sanitize_region_mappings(item)
            merged.append(item)
    return merged


def best_region_for_key(regions, key, region_type, detail_roi):
    candidates = []
    for item in regions:
        if item.get("region_type") != region_type:
            continue
        if any((int(m.get("canonical_leg_index") or 0), m.get("field_name")) == key for m in item.get("candidate_mappings", [])):
            candidates.append(item)
    if len(candidates) <= 1:
        return candidates
    center_x = detail_roi["x_center"]
    center_y = detail_roi["y_center"]
    candidates.sort(key=lambda item: (-float(item.get("confidence") or 0), abs(item["bbox"]["x_center"] - center_x) + abs(item["bbox"]["y_center"] - center_y), item["bbox"]["width"] * item["bbox"]["height"]))
    return candidates[:1]


def limit_duplicate_evidence(regions, detail_roi):
    keep_ids = set()
    for item in regions:
        if not item.get("candidate_mappings"):
            keep_ids.add(id(item))
            continue
        for item_mapping in item.get("candidate_mappings", []):
            key = (int(item_mapping.get("canonical_leg_index") or 0), item_mapping.get("field_name"))
            selected = best_region_for_key(regions, key, item.get("region_type"), detail_roi)
            if item in selected:
                keep_ids.add(id(item))
    return [item for item in regions if id(item) in keep_ids]


def fallback_box_for_meta(meta, target, detail_roi):
    legs = target.get("candidate_legs", [])
    leg_count = max(1, len(legs))
    leg_index = max(1, int(meta.get("canonical_leg_index") or 1))
    left = detail_roi["x_center"] - detail_roi["width"] / 2
    top = detail_roi["y_center"] - detail_roi["height"] / 2
    cell_w = detail_roi["width"] / leg_count
    cx = left + cell_w * (leg_index - 0.5)
    field = meta["field_name"]
    leg_type = meta.get("leg_type")
    if field == "Q2_altitude_constraint":
        return "ALTITUDE_TEXT", bbox(cx, top + detail_roi["height"] * 0.25, cell_w * 0.78, detail_roi["height"] * 0.16)
    if field == "Q1_fix_ident":
        return "FIX_TEXT", bbox(cx, top + detail_roi["height"] * 0.35, cell_w * 0.82, detail_roi["height"] * 0.18)
    if field == "Q4_course_or_radial":
        return "RADIAL_TEXT" if leg_type in {"CF", "FA", "FC", "FD", "FM"} else "TRACK_OR_RADIAL_TEXT", bbox(cx, top + detail_roi["height"] * 0.55, cell_w * 0.9, detail_roi["height"] * 0.18)
    if field == "Q3_turn":
        return "PATH_SEGMENT", bbox(cx, top + detail_roi["height"] * 0.55, cell_w * 0.86, detail_roi["height"] * 0.52)
    if field == "Q5_hold_params":
        return "HOLDING_PATTERN", bbox(cx, top + detail_roi["height"] * 0.62, cell_w * 0.88, detail_roi["height"] * 0.64)
    return "FIX_TEXT", bbox(cx, top + detail_roi["height"] * 0.5, cell_w * 0.75, detail_roi["height"] * 0.2)


def add_fallback_for_uncovered(chart_id, serial, target, lookup, detail_roi, regions):
    covered = covered_keys(regions)
    output = []
    for key, meta in sorted(lookup.items()):
        if key[1] == "Q_terminator" or key in covered:
            continue
        region_type, box = fallback_box_for_meta(meta, target, detail_roi)
        output.append(region(
            chart_id,
            serial,
            region_type,
            box,
            f"low-confidence fallback for {meta['expected_value']}",
            [mapping(meta, "fallback lower-detail candidate because no reliable icon/text detection covered this PR28 field", 0.22)],
            confidence=0.22,
            source="fallback_inside_detected_detail_area",
        ))
        serial += 1
    return output, serial


def generate_chart(manifest_item, target):
    chart_id = manifest_item["chart_id"]
    prelabel_path = FORMAL / "prelabels" / f"{chart_id}.json"
    prelabel = read_json(prelabel_path)
    lookup = target_lookup(target)
    coarse = [item for item in prelabel.get("regions", []) if item.get("region_type") in COARSE_TYPES]
    existing_fine = [item for item in prelabel.get("regions", []) if item.get("region_type") not in COARSE_TYPES]
    copied = adapt_pilot_regions(chart_id, lookup)

    pdf_path = FORMAL / "pdfs" / manifest_item["pdf_file"]
    image_path = resolve_workspace_path(manifest_item["image_path"])
    if not pdf_path.exists():
        detail_roi = next((item["bbox"] for item in coarse if item.get("region_type") == "MISSED_APPROACH_DETAIL_AREA"), None) or DEFAULT_LOWER_ROI
        all_fine = merge_overlapping_regions(copied + deepcopy(existing_fine))
        all_fine = sanitize_region_list(all_fine)
        all_fine = limit_duplicate_evidence(all_fine, detail_roi)
        sanitized_regions = coarse + all_fine
        if sanitized_regions != prelabel.get("regions", []):
            prelabel["regions"] = sanitized_regions
            prelabel["prelabel_version"] = "v0.29-formal300-typed-visible-evidence"
            prelabel["generated_at"] = datetime.now(timezone.utc).isoformat()
            prelabel.setdefault("generation_policy", {})
            prelabel["generation_policy"].update({
                "formal300_small_box_prelabels_added": True,
                "small_box_source": "preserved existing fine boxes because source PDFs are unavailable; sanitized field mappings by region type and visible label text",
                "small_box_final_ground_truth": False,
                "small_box_human_calibration_required": True,
                "candidate_mappings_are_cifp424_targets_not_independent_predictions": True,
                "compound_q4_and_q_terminator_candidate_mappings": True,
                "field_mapping_region_type_sanitizer": True,
                "field_mapping_visible_text_sanitizer": True,
                "fine_q_terminator_mappings_removed": True,
                "hm_inherited_fix_alt_fine_mappings_removed": True,
                "generic_path_hold_graphics_removed_from_q5_params": True,
                "source_pdfs_available": False,
            })
            write_json(prelabel_path, prelabel)
        return {
            "chart_id": chart_id,
            "coarse_count": len(coarse),
            "pilot_copy_count": 0,
            "pdf_text_box_count": 0,
            "cv_symbol_box_count": 0,
            "fine_count": len(all_fine),
            "match_count": 0,
            "selected_match_count": 0,
            "detail_roi": detail_roi,
            "source_pdfs_available": False,
        }

    words = pdf_words(pdf_path)
    matches = word_matches(words, lookup)
    detail_roi, selected_matches = choose_detail_roi({"regions": coarse}, matches, image_path)
    detail_region = next((item for item in coarse if item.get("region_type") == "MISSED_APPROACH_DETAIL_AREA"), None)
    if detail_region:
        detail_region["bbox"] = detail_roi
        detail_region["label"] = "lower/profile missed-approach detail area detected from PDF text/icon anchors"
        detail_region["source_layer"] = "pdf_text_cluster_icon_area_detector"
        detail_region["confidence"] = 0.5 if selected_matches else 0.28

    serial = 1
    text_regions, serial = add_text_boxes(chart_id, serial, selected_matches, lookup, detail_roi, copied)
    symbol_regions, serial = add_symbol_boxes(chart_id, serial, image_path, detail_roi, lookup, copied + text_regions)

    # Keep reviewed pilot boxes first, then add detections for fields/visual evidence not already covered.
    all_fine = merge_overlapping_regions(copied + text_regions + symbol_regions)
    all_fine = limit_duplicate_evidence(all_fine, detail_roi)
    fallback_regions = []
    if ENABLE_LOW_CONFIDENCE_FALLBACK_BOXES:
        fallback_regions, serial = add_fallback_for_uncovered(chart_id, serial, target, lookup, detail_roi, all_fine)
    all_fine = merge_overlapping_regions(all_fine + fallback_regions)
    add_compound_support_mappings(coarse + all_fine, lookup)
    all_fine = sanitize_region_list(all_fine)
    prelabel["regions"] = coarse + all_fine
    prelabel["prelabel_version"] = "v0.29-formal300-structure-aware-typed-visible-evidence"
    prelabel["generated_at"] = datetime.now(timezone.utc).isoformat()
    prelabel.setdefault("generation_policy", {})
    prelabel["generation_policy"].update({
        "formal300_small_box_prelabels_added": True,
        "small_box_source": "score lower missed-approach detail candidates with PR28 text anchors, boxed-cell structure, CV icon components, and compound leg evidence; only detected evidence is drawn",
        "small_box_final_ground_truth": False,
        "small_box_human_calibration_required": True,
        "missed_approach_icon_or_detail_area_first": True,
        "boxed_cell_structure_weighted": True,
        "candidate_mappings_are_cifp424_targets_not_independent_predictions": True,
        "compound_q4_and_q_terminator_candidate_mappings": True,
        "field_mapping_region_type_sanitizer": True,
        "field_mapping_visible_text_sanitizer": True,
        "fine_q_terminator_mappings_removed": True,
        "hm_inherited_fix_alt_fine_mappings_removed": True,
        "generic_path_hold_graphics_removed_from_q5_params": True,
        "low_confidence_blank_fallback_boxes_enabled": ENABLE_LOW_CONFIDENCE_FALLBACK_BOXES,
    })
    write_json(prelabel_path, prelabel)
    return {
        "chart_id": chart_id,
        "coarse_count": len(coarse),
        "pilot_copy_count": len(copied),
        "pdf_text_box_count": len(text_regions),
        "cv_symbol_box_count": len(symbol_regions),
        "fine_count": len(all_fine),
        "match_count": len(matches),
        "selected_match_count": len(selected_matches),
        "detail_roi": detail_roi,
        "source_pdfs_available": True,
    }


def main():
    manifest = read_json(FORMAL / "manifest.json")
    targets = {item["chart_id"]: item for item in read_json(FORMAL / "targets/canonical_targets.json")}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "formal300",
        "method": "structure-aware lower missed-approach detail first: PR28 text anchors + boxed-cell scoring + CV icon/symbol components",
        "final_ground_truth": False,
        "human_calibration_required": True,
        "charts": [],
    }
    for item in manifest:
        report["charts"].append(generate_chart(item, targets[item["chart_id"]]))
    write_json(FORMAL / "reports/formal300_icon_aligned_prelabels_report.json", report)
    fine_counts = [item["fine_count"] for item in report["charts"]]
    text_counts = [item["pdf_text_box_count"] for item in report["charts"]]
    symbol_counts = [item["cv_symbol_box_count"] for item in report["charts"]]
    print(f"Updated {len(report['charts'])} formal300 prelabels")
    print(f"fine boxes min/avg/max: {min(fine_counts)} / {sum(fine_counts)/len(fine_counts):.1f} / {max(fine_counts)}")
    print(f"pdf text boxes total: {sum(text_counts)}")
    print(f"cv symbol boxes total: {sum(symbol_counts)}")


if __name__ == "__main__":
    main()
