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
MAX_DETAIL_CELL_WIDTH = 0.18
MAX_DETAIL_GROUP_WIDTH = 0.42
MAX_EMPTY_NEIGHBOR_EXPANSION = 2
COARSE_SEED_BOXES = {
    "MISSED_APPROACH_TEXT": {"x_center": 0.805, "y_center": 0.142, "width": 0.33, "height": 0.07},
    "PLAN_VIEW": {"x_center": 0.5, "y_center": 0.43, "width": 0.94, "height": 0.48},
    "MISSED_APPROACH_DETAIL_AREA": DEFAULT_LOWER_ROI,
}
ENABLE_LOW_CONFIDENCE_FALLBACK_BOXES = False
ENABLE_PRACTICE_PILOT_COPY = False
REQUIRE_SOURCE_PDFS_FOR_FINE_PRELABELS = True


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
    # The best row locates the lower-detail strip, but fields in the same strip
    # can be on adjacent rows (for example "hdg 063" below altitude/fix cells).
    selected = [item for item in matches if in_roi(item["word"], text_roi, pad=0.0)]
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
    if not ENABLE_PRACTICE_PILOT_COPY:
        return []
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


def bbox_from_pixel_edges(x0, y0, x1, y1, image_width, image_height):
    left = max(0.0, min(1.0, x0 / image_width))
    right = max(0.0, min(1.0, x1 / image_width))
    top = max(0.0, min(1.0, y0 / image_height))
    bottom = max(0.0, min(1.0, y1 / image_height))
    return {
        "x_center": round((left + right) / 2, 4),
        "y_center": round((top + bottom) / 2, 4),
        "width": round(max(0.004, right - left), 4),
        "height": round(max(0.004, bottom - top), 4),
    }


def bbox_from_norm_edges(left, top, right, bottom):
    left = max(0.0, min(1.0, left))
    right = max(0.0, min(1.0, right))
    top = max(0.0, min(1.0, top))
    bottom = max(0.0, min(1.0, bottom))
    if right <= left + 0.004 or bottom <= top + 0.004:
        return None
    return {
        "x_center": round((left + right) / 2, 4),
        "y_center": round((top + bottom) / 2, 4),
        "width": round(right - left, 4),
        "height": round(bottom - top, 4),
    }


def bbox_from_pixels(x, y, w, h, image_width, image_height):
    return bbox((x + w / 2) / image_width, (y + h / 2) / image_height, w / image_width, h / image_height)


def segment_overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def detect_chart_table_lines(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return [], [], 0, 0
    image_height, image_width = image.shape[:2]
    dark = cv2.threshold(image, 180, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal = cv2.morphologyEx(
        dark,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, image_width // 30), 1)),
    )
    vertical = cv2.morphologyEx(
        dark,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, image_height // 45))),
    )
    horizontal_lines = []
    contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width >= 25 and height <= 8:
            horizontal_lines.append({
                "x0": float(x),
                "x1": float(x + width),
                "y": float(y + height / 2),
                "length": float(width),
            })
    vertical_lines = []
    contours, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if height >= 25 and width <= 8:
            vertical_lines.append({
                "x": float(x + width / 2),
                "y0": float(y),
                "y1": float(y + height),
                "length": float(height),
            })
    return horizontal_lines, vertical_lines, image_width, image_height


def horizontal_line_bands(horizontal_lines, image_width, image_height, y_tolerance_px=8):
    if not image_width or not image_height:
        return []
    bands = []
    for line in sorted(horizontal_lines, key=lambda item: item["y"]):
        y_norm = line["y"] / image_height
        interval = (line["x0"] / image_width, line["x1"] / image_width)
        target = None
        for band in bands:
            if abs(band["y_px"] - line["y"]) <= y_tolerance_px:
                target = band
                break
        if target is None:
            target = {"y_px": line["y"], "y": y_norm, "intervals": [], "length": 0.0, "count": 0}
            bands.append(target)
        target["intervals"].append(interval)
        target["length"] += line["length"] / image_width
        target["count"] += 1
        # Weighted enough for split AIP table lines, but still keeps nearby unrelated
        # rows separate when they are more than a few pixels apart.
        target["y_px"] = (target["y_px"] * (target["count"] - 1) + line["y"]) / target["count"]
        target["y"] = target["y_px"] / image_height
    for band in bands:
        band["x0"] = min(interval[0] for interval in band["intervals"])
        band["x1"] = max(interval[1] for interval in band["intervals"])
    return bands


def vertical_line_bands(vertical_lines, image_width, image_height, x_tolerance_px=6):
    if not image_width or not image_height:
        return []
    bands = []
    for line in sorted(vertical_lines, key=lambda item: item["x"]):
        x_norm = line["x"] / image_width
        interval = (line["y0"] / image_height, line["y1"] / image_height)
        target = None
        for band in bands:
            if abs(band["x_px"] - line["x"]) <= x_tolerance_px:
                target = band
                break
        if target is None:
            target = {"x_px": line["x"], "x": x_norm, "intervals": [], "length": 0.0, "count": 0}
            bands.append(target)
        target["intervals"].append(interval)
        target["length"] += line["length"] / image_height
        target["count"] += 1
        target["x_px"] = (target["x_px"] * (target["count"] - 1) + line["x"]) / target["count"]
        target["x"] = target["x_px"] / image_width
    for band in bands:
        band["y0"] = min(interval[0] for interval in band["intervals"])
        band["y1"] = max(interval[1] for interval in band["intervals"])
    return bands


def band_contains_x(band, x, pad=0.0):
    return any(left - pad <= x <= right + pad for left, right in band["intervals"])


def vertical_band_overlap_with_span(band, top, bottom):
    return sum(segment_overlap(interval_top, interval_bottom, top, bottom) for interval_top, interval_bottom in band["intervals"])


def band_overlap_with_span(band, left, right):
    return sum(segment_overlap(interval_left, interval_right, left, right) for interval_left, interval_right in band["intervals"])


def horizontal_band_covers_span(band, left, right, pad=0.006, min_ratio=0.82):
    if not band:
        return False
    width = max(right - left, 0.001)
    if any(interval_left <= left + pad and interval_right >= right - pad for interval_left, interval_right in band["intervals"]):
        return True
    return band_overlap_with_span(band, left, right) >= width * min_ratio


def vertical_band_spans_edges(band, top, bottom, pad=0.006, min_ratio=0.82):
    if not band:
        return False
    height = max(bottom - top, 0.001)
    return any(
        interval_top <= top + pad
        and interval_bottom >= bottom - pad
        and segment_overlap(interval_top, interval_bottom, top, bottom) >= height * min_ratio
        for interval_top, interval_bottom in band["intervals"]
    )


def match_center(item):
    box = item["word"]["bbox"]
    return box["x_center"], box["y_center"]


def match_inside_edges(item, left, top, right, bottom, pad=0.004):
    x, y = match_center(item)
    return left - pad <= x <= right + pad and top - pad <= y <= bottom + pad


def closed_detail_cells(horizontal_bands, vertical_bands, top_band):
    if not top_band:
        return []
    top = top_band["y"]
    output = []
    bottom_candidates = [
        band for band in horizontal_bands
        if top + 0.018 <= band["y"] <= top + 0.15
        and band["length"] >= 0.035
    ]
    for bottom_band in bottom_candidates:
        bottom = bottom_band["y"]
        usable_verticals = sorted(
            [
                band for band in vertical_bands
                if vertical_band_spans_edges(band, top, bottom)
            ],
            key=lambda band: band["x"],
        )
        if len(usable_verticals) < 2:
            continue
        for left_band, right_band in zip(usable_verticals, usable_verticals[1:]):
            left = left_band["x"]
            right = right_band["x"]
            width = right - left
            if width < 0.018 or width > MAX_DETAIL_CELL_WIDTH:
                continue
            if not horizontal_band_covers_span(top_band, left, right):
                continue
            if not horizontal_band_covers_span(bottom_band, left, right):
                continue
            output.append({
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "top_band": top_band,
                "bottom_band": bottom_band,
            })
    return output


def vertical_edge_span_groups(vertical_bands):
    spans = []
    for band in vertical_bands:
        for interval_top, interval_bottom in band["intervals"]:
            height = interval_bottom - interval_top
            if not 0.035 <= height <= 0.095:
                continue
            if not 0.58 <= interval_top <= 0.76:
                continue
            if not 0.62 <= interval_bottom <= 0.82:
                continue
            spans.append((interval_top, interval_bottom))
    groups = []
    for top, bottom in sorted(spans):
        target = None
        for group in groups:
            if abs(group["top"] - top) <= 0.008 and abs(group["bottom"] - bottom) <= 0.01:
                target = group
                break
        if target is None:
            target = {"top": top, "bottom": bottom, "count": 0}
            groups.append(target)
        target["top"] = (target["top"] * target["count"] + top) / (target["count"] + 1)
        target["bottom"] = (target["bottom"] * target["count"] + bottom) / (target["count"] + 1)
        target["count"] += 1
    return [group for group in groups if group["count"] >= 2]


def vertical_edge_detail_cells(horizontal_bands, vertical_bands):
    output = []
    for span in vertical_edge_span_groups(vertical_bands):
        top = span["top"]
        bottom = span["bottom"]
        usable_verticals = sorted(
            [band for band in vertical_bands if vertical_band_spans_edges(band, top, bottom, pad=0.008, min_ratio=0.78)],
            key=lambda band: band["x"],
        )
        if len(usable_verticals) < 2:
            continue
        near_top = find_band_near_y(horizontal_bands, top, tolerance=0.01)
        near_bottom = find_band_near_y(horizontal_bands, bottom, tolerance=0.012)
        for left_band, right_band in zip(usable_verticals, usable_verticals[1:]):
            left = left_band["x"]
            right = right_band["x"]
            width = right - left
            if width < 0.018 or width > MAX_DETAIL_CELL_WIDTH:
                continue
            top_covered = near_top and horizontal_band_covers_span(near_top, left, right, pad=0.008, min_ratio=0.70)
            bottom_covered = near_bottom and horizontal_band_covers_span(near_bottom, left, right, pad=0.008, min_ratio=0.70)
            inferred_top_from_aligned_corners = bool(bottom_covered and span["count"] >= 4)
            if not (bottom_covered and (top_covered or inferred_top_from_aligned_corners)):
                continue
            output.append({
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "top_band": near_top,
                "bottom_band": near_bottom,
            })
    return output


def field_diversity(matches):
    return len({(item["key"][0], item["meta"]["field_name"]) for item in matches})


def cell_width(cell):
    return cell["right"] - cell["left"]


def cell_range_width(row_cells, left_index, right_index):
    return row_cells[right_index]["right"] - row_cells[left_index]["left"]


def expand_adjacent_detail_cells(row_cells, left_index, right_index):
    for _ in range(MAX_EMPTY_NEIGHBOR_EXPANSION):
        if left_index <= 0:
            break
        candidate = row_cells[left_index - 1]
        if cell_width(candidate) > MAX_DETAIL_CELL_WIDTH:
            break
        if row_cells[right_index]["right"] - candidate["left"] > MAX_DETAIL_GROUP_WIDTH:
            break
        left_index -= 1
    for _ in range(MAX_EMPTY_NEIGHBOR_EXPANSION):
        if right_index + 1 >= len(row_cells):
            break
        candidate = row_cells[right_index + 1]
        if cell_width(candidate) > MAX_DETAIL_CELL_WIDTH:
            break
        if candidate["right"] - row_cells[left_index]["left"] > MAX_DETAIL_GROUP_WIDTH:
            break
        right_index += 1
    return left_index, right_index


def choose_cell_group_from_cells(cells, anchor_matches, all_matches):
    if not cells:
        return None
    anchor_matches = anchor_matches or []
    all_matches = all_matches or anchor_matches
    candidates = []
    rows = {}
    for cell in cells:
        rows.setdefault(round(cell["bottom"], 4), []).append(cell)
    for row_cells in rows.values():
        row_cells = sorted(row_cells, key=lambda cell: cell["left"])
        anchor_indexes = []
        all_match_indexes = []
        for index, cell in enumerate(row_cells):
            if any(match_inside_edges(item, cell["left"], cell["top"], cell["right"], cell["bottom"], pad=0.006) for item in anchor_matches):
                anchor_indexes.append(index)
            if any(match_inside_edges(item, cell["left"], cell["top"], cell["right"], cell["bottom"], pad=0.006) for item in all_matches):
                all_match_indexes.append(index)
        if not anchor_indexes:
            # The text scorer can lock onto profile-view duplicates. If the
            # actual boxed icon/detail row contains target evidence, prefer the
            # closed row over a non-cell profile rectangle.
            anchor_indexes = all_match_indexes[:]
            if not anchor_indexes:
                continue
            seed_from_all_matches = True
        else:
            seed_from_all_matches = False

        indexes = sorted(set(anchor_indexes + all_match_indexes))
        left_index = min(indexes)
        right_index = max(indexes)
        if cell_range_width(row_cells, left_index, right_index) > MAX_DETAIL_GROUP_WIDTH:
            left_index = min(anchor_indexes)
            right_index = max(anchor_indexes)

        left_index, right_index = expand_adjacent_detail_cells(row_cells, left_index, right_index)

        group = row_cells[left_index:right_index + 1]
        left = min(cell["left"] for cell in group)
        right = max(cell["right"] for cell in group)
        top = group[0]["top"]
        bottom = group[0]["bottom"]
        group_matches = [item for item in all_matches if match_inside_edges(item, left, top, right, bottom, pad=0.008)]
        anchor_hits = [item for item in anchor_matches if match_inside_edges(item, left, top, right, bottom, pad=0.008)]
        if not group_matches or (not anchor_hits and not seed_from_all_matches):
            continue
        width = right - left
        height = bottom - top
        score = (
            len(anchor_hits) * 18.0
            + len(group_matches) * 7.0
            + field_diversity(group_matches) * 9.0
            + len(group) * 1.2
            - (8.0 if seed_from_all_matches else 0.0)
            - width * 22.0
            - height * 18.0
            - max(0.0, top - 0.72) * 80.0
        )
        candidates.append((score, left, top, right, bottom, group_matches))
    if not candidates:
        return None
    _, left, top, right, bottom, group_matches = max(candidates, key=lambda item: item[0])
    refined = bbox_from_norm_edges(left, top, right, bottom)
    if not refined:
        return None
    return refined, group_matches


def choose_closed_detail_roi(horizontal_bands, vertical_bands, top_band, anchor_matches, all_matches):
    return choose_cell_group_from_cells(closed_detail_cells(horizontal_bands, vertical_bands, top_band), anchor_matches, all_matches)


def choose_vertical_edge_detail_roi(horizontal_bands, vertical_bands, anchor_matches, all_matches):
    return choose_cell_group_from_cells(vertical_edge_detail_cells(horizontal_bands, vertical_bands), anchor_matches, all_matches)


def choose_detail_top_band(bands, matches):
    if not matches:
        return None
    boxes = [item["word"]["bbox"] for item in matches]
    content = bbox_union(boxes, pad_x=0.0, pad_y=0.0)
    if not content:
        return None
    left, top, right, bottom = box_edges(content)
    span_width = max(right - left, 0.001)
    median_y = sorted(item["word"]["bbox"]["y_center"] for item in matches)[len(matches) // 2]
    candidates = []
    for band in bands:
        y = band["y"]
        if not 0.54 <= y <= 0.78:
            continue
        overlap_ratio = band_overlap_with_span(band, left, right) / span_width
        center_hits = sum(1 for item in matches if band_contains_x(band, item["word"]["bbox"]["x_center"], pad=0.012))
        if overlap_ratio < 0.28 and center_hits == 0:
            continue
        window_bottom = y + 0.082
        below = [
            item for item in matches
            if y - 0.002 <= item["word"]["bbox"]["y_center"] <= window_bottom
            and band_contains_x(band, item["word"]["bbox"]["x_center"], pad=0.012)
        ]
        above = [
            item for item in matches
            if item["word"]["bbox"]["y_center"] < y - 0.002
            and left - 0.015 <= item["word"]["bbox"]["x_center"] <= right + 0.015
        ]
        outside_window_below = [
            item for item in matches
            if item["word"]["bbox"]["y_center"] > window_bottom
            and band_contains_x(band, item["word"]["bbox"]["x_center"], pad=0.012)
        ]
        if not below:
            continue
        altitude_hits = sum(1 for item in below if item["meta"]["field_name"] == "Q2_altitude_constraint")
        score = (
            len(below) * 12.0
            + altitude_hits * 5.0
            - len(above) * 7.0
            - len(outside_window_below) * 4.0
            + min(overlap_ratio, 1.0) * 8.0
            + min(float(band.get("length") or 0.0), 1.0) * 2.0
            - abs(y - median_y) * 45.0
        )
        candidates.append((score, band, below))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def choose_detail_bottom_band(bands, filtered_matches, top_band):
    if not filtered_matches or not top_band:
        return None
    content = bbox_union([item["word"]["bbox"] for item in filtered_matches], pad_x=0.0, pad_y=0.0)
    if not content:
        return None
    left, top, right, bottom = box_edges(content)
    span_width = max(right - left, 0.001)
    min_bottom = max(top_band["y"] + 0.018, bottom - 0.004)
    candidates = []
    for band in bands:
        y = band["y"]
        if y <= min_bottom or y > top_band["y"] + 0.13:
            continue
        overlap_ratio = band_overlap_with_span(band, left, right) / span_width
        if overlap_ratio < 0.22 and not any(band_contains_x(band, item["word"]["bbox"]["x_center"], pad=0.012) for item in filtered_matches):
            continue
        score = -abs(y - bottom) * 95.0 + min(overlap_ratio, 1.0) * 8.0 + min(float(band.get("length") or 0.0), 1.0)
        candidates.append((score, band))
    if not candidates:
        loose = [
            band for band in bands
            if top_band["y"] + 0.018 < band["y"] <= top_band["y"] + 0.13
        ]
        if not loose:
            return None
        return min(loose, key=lambda band: abs(band["y"] - bottom))
    return max(candidates, key=lambda item: item[0])[1]


def line_locked_x_bounds(vertical_bands, top_band, bottom_band, filtered_matches, top, bottom):
    content = bbox_union([item["word"]["bbox"] for item in filtered_matches], pad_x=0.0, pad_y=0.0)
    if not content:
        return None
    content_left, _, content_right, _ = box_edges(content)
    span_height = max(bottom - top, 0.001)
    usable_verticals = [
        band for band in vertical_bands
        if vertical_band_overlap_with_span(band, top, bottom) >= span_height * 0.42
    ]
    left_candidates = [band for band in usable_verticals if band["x"] <= content_left + 0.004]
    right_candidates = [band for band in usable_verticals if band["x"] >= content_right - 0.004]
    left = max(left_candidates, key=lambda band: band["x"])["x"] if left_candidates else None
    right = min(right_candidates, key=lambda band: band["x"])["x"] if right_candidates else None

    if left is not None and right is not None and right > left + 0.01:
        return left, right

    intervals = []
    for band in [top_band, bottom_band]:
        if not band:
            continue
        intervals.extend([
            interval for interval in band["intervals"]
            if interval[1] >= content_left - 0.02 and interval[0] <= content_right + 0.02
        ])
    if intervals:
        left = max(interval[0] for interval in intervals if interval[0] <= content_left + 0.004) if any(interval[0] <= content_left + 0.004 for interval in intervals) else min(interval[0] for interval in intervals)
        right = min(interval[1] for interval in intervals if interval[1] >= content_right - 0.004) if any(interval[1] >= content_right - 0.004 for interval in intervals) else max(interval[1] for interval in intervals)
        if right > left + 0.01:
            return left, right
    return None


def find_band_near_y(bands, y, tolerance=0.006):
    candidates = [band for band in bands if abs(band["y"] - y) <= tolerance]
    if not candidates:
        return None
    return max(candidates, key=lambda band: float(band.get("length") or 0.0))


def choose_plan_view_box(image_path):
    horizontal_lines, vertical_lines, image_width, image_height = detect_chart_table_lines(image_path)
    bands = horizontal_line_bands(horizontal_lines, image_width, image_height)
    full_width_candidates = [
        band for band in bands
        if 0.14 <= band["y"] <= 0.36
        and band["length"] >= 0.74
        and band["x0"] <= 0.075
        and band["x1"] >= 0.90
    ]
    lower_candidates = [
        band for band in bands
        if 0.50 <= band["y"] <= 0.74
        and band["length"] >= 0.54
    ]
    if not full_width_candidates or not lower_candidates:
        return None, None, None
    top_band = max(full_width_candidates, key=lambda band: band["y"])
    bottom_band = max(
        lower_candidates,
        key=lambda band: (
            min(float(band.get("length") or 0.0), 0.75) * 4.0
            - abs(band["y"] - 0.64) * 5.0
            - max(0.0, top_band["y"] + 0.25 - band["y"]) * 8.0
        ),
    )
    left = min(interval[0] for interval in top_band["intervals"])
    right = max(interval[1] for interval in top_band["intervals"])
    plan_box = bbox_from_norm_edges(left, top_band["y"], right, bottom_band["y"])
    return plan_box, top_band, bottom_band


def refine_detail_roi_to_lower_strip(image_path, detail_roi, selected_matches, strip_top_y=None, all_matches=None):
    horizontal_lines, vertical_lines, image_width, image_height = detect_chart_table_lines(image_path)
    bands = horizontal_line_bands(horizontal_lines, image_width, image_height)
    vertical_bands = vertical_line_bands(vertical_lines, image_width, image_height)
    all_matches = all_matches or selected_matches
    top_band = find_band_near_y(bands, strip_top_y) if strip_top_y is not None else None
    if top_band is None:
        top_band = choose_detail_top_band(bands, selected_matches)
    if not top_band:
        vertical_edge_choice = choose_vertical_edge_detail_roi(bands, vertical_bands, selected_matches, all_matches)
        return vertical_edge_choice or (detail_roi, selected_matches)

    closed_choice = choose_closed_detail_roi(bands, vertical_bands, top_band, selected_matches, all_matches)
    if closed_choice:
        return closed_choice
    vertical_edge_choice = choose_vertical_edge_detail_roi(bands, vertical_bands, selected_matches, all_matches)
    if vertical_edge_choice:
        return vertical_edge_choice

    filtered = [
        item for item in selected_matches
        if item["word"]["bbox"]["y_center"] >= top_band["y"] - 0.002
        and band_contains_x(top_band, item["word"]["bbox"]["x_center"], pad=0.012)
    ]
    if not filtered:
        return detail_roi, selected_matches

    content = bbox_union([item["word"]["bbox"] for item in filtered], pad_x=0.0, pad_y=0.0)
    if not content:
        return detail_roi, selected_matches
    content_left, content_top, content_right, content_bottom = box_edges(content)
    bottom_band = choose_detail_bottom_band(bands, filtered, top_band)
    if not bottom_band:
        return detail_roi, selected_matches
    bottom = bottom_band["y"]
    x_bounds = line_locked_x_bounds(vertical_bands, top_band, bottom_band, filtered, top_band["y"], bottom)
    if not x_bounds:
        return detail_roi, selected_matches
    left, right = x_bounds
    refined = bbox_from_norm_edges(left, top_band["y"], right, bottom)
    if not refined:
        return detail_roi, selected_matches
    return refined, filtered


def clamp_plan_view_above_detail(coarse_regions, detail_roi):
    detail_top = detail_roi["y_center"] - detail_roi["height"] / 2
    for item in coarse_regions:
        if item.get("region_type") != "PLAN_VIEW":
            continue
        left, top, right, bottom = box_edges(item["bbox"])
        if bottom > detail_top:
            updated = bbox_from_norm_edges(left, top, right, detail_top)
            if updated:
                item["bbox"] = updated
                item["source_layer"] = f"{item.get('source_layer', 'aip_table_line_snap')}+clamped_above_lower_detail"
    return coarse_regions


def snap_bbox_to_table_lines(image_path, seed_box, content_box=None, search_px=70, content_axes="both"):
    horizontal_lines, vertical_lines, image_width, image_height = detect_chart_table_lines(image_path)
    if not image_width or not image_height:
        return seed_box
    seed_x0, seed_y0, seed_x1, seed_y1 = pixel_rect_from_bbox(seed_box, image_width, image_height)
    ref_box = content_box or seed_box
    ref_x0, ref_y0, ref_x1, ref_y1 = pixel_rect_from_bbox(ref_box, image_width, image_height)
    seed_width = max(seed_x1 - seed_x0, 1)
    seed_height = max(seed_y1 - seed_y0, 1)
    ref_width = max(ref_x1 - ref_x0, 1)
    ref_height = max(ref_y1 - ref_y0, 1)

    use_content_y = content_box is not None and content_axes in {"both", "y"}
    use_content_x = content_box is not None and content_axes in {"both", "x"}

    def horizontal_candidates(edge_y, ref_y, want_after):
        candidates = []
        for line in horizontal_lines:
            if abs(line["y"] - edge_y) > search_px and abs(line["y"] - ref_y) > search_px:
                continue
            overlap = segment_overlap(line["x0"], line["x1"], seed_x0, seed_x1)
            ref_overlap = segment_overlap(line["x0"], line["x1"], ref_x0, ref_x1)
            if overlap < seed_width * 0.30 and ref_overlap < ref_width * 0.60:
                continue
            if line["length"] < min(seed_width * 0.30, ref_width * 0.80):
                continue
            if use_content_y and want_after and line["y"] < ref_y1 - 3:
                continue
            if use_content_y and not want_after and line["y"] > ref_y0 + 3:
                continue
            candidates.append(line)
        if not candidates:
            return None
        return min(candidates, key=lambda line: abs(line["y"] - ref_y) if use_content_y else abs(line["y"] - edge_y))

    def vertical_candidates(edge_x, ref_x, want_after):
        candidates = []
        for line in vertical_lines:
            if abs(line["x"] - edge_x) > search_px and abs(line["x"] - ref_x) > search_px:
                continue
            overlap = segment_overlap(line["y0"], line["y1"], seed_y0, seed_y1)
            ref_overlap = segment_overlap(line["y0"], line["y1"], ref_y0, ref_y1)
            if overlap < seed_height * 0.30 and ref_overlap < ref_height * 0.60:
                continue
            if line["length"] < min(seed_height * 0.30, ref_height * 0.80):
                continue
            if use_content_x and want_after and line["x"] < ref_x1 - 3:
                continue
            if use_content_x and not want_after and line["x"] > ref_x0 + 3:
                continue
            candidates.append(line)
        if not candidates:
            return None
        return min(candidates, key=lambda line: abs(line["x"] - ref_x) if use_content_x else abs(line["x"] - edge_x))

    top = horizontal_candidates(seed_y0, ref_y0, False)
    bottom = horizontal_candidates(seed_y1, ref_y1, True)
    left = vertical_candidates(seed_x0, ref_x0, False)
    right = vertical_candidates(seed_x1, ref_x1, True)
    snapped_x0 = left["x"] if left else seed_x0
    snapped_x1 = right["x"] if right else seed_x1
    snapped_y0 = top["y"] if top else seed_y0
    snapped_y1 = bottom["y"] if bottom else seed_y1
    if snapped_x1 <= snapped_x0 + 5 or snapped_y1 <= snapped_y0 + 5:
        return seed_box
    return bbox_from_pixel_edges(snapped_x0, snapped_y0, snapped_x1, snapped_y1, image_width, image_height)


def words_content_bbox(words, container_box, pad=0.002, max_y_center=None):
    selected = [
        item["bbox"] for item in words
        if in_roi(item, container_box, pad=0.0)
        and (max_y_center is None or item["bbox"]["y_center"] <= max_y_center)
    ]
    return bbox_union(selected, pad_x=pad, pad_y=pad) if selected else None


def snap_coarse_regions_to_chart_boxes(coarse_regions, image_path, words):
    plan_box, _, _ = choose_plan_view_box(image_path)
    for item in coarse_regions:
        region_type = item.get("region_type")
        if region_type in COARSE_SEED_BOXES:
            item["bbox"] = deepcopy(COARSE_SEED_BOXES[region_type])
        if region_type == "MISSED_APPROACH_TEXT":
            top = item["bbox"]["y_center"] - item["bbox"]["height"] / 2
            cutoff = top + item["bbox"]["height"] * 0.75
            content = words_content_bbox(words, item["bbox"], pad=0.002, max_y_center=cutoff)
            item["bbox"] = snap_bbox_to_table_lines(image_path, item["bbox"], content_box=content, search_px=75, content_axes="y")
            item["source_layer"] = "aip_table_line_snap"
            item["confidence"] = max(float(item.get("confidence") or 0), 0.58)
        elif region_type == "PLAN_VIEW":
            if plan_box:
                item["bbox"] = plan_box
                item["source_layer"] = "aip_long_line_plan_view_snap"
            else:
                item["bbox"] = snap_bbox_to_table_lines(image_path, item["bbox"], content_box=None, search_px=75)
                item["source_layer"] = "aip_table_line_snap"
            item["confidence"] = max(float(item.get("confidence") or 0), 0.5)
    return coarse_regions


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


def clean_pdf_display_text(text):
    return str(text or "").replace("Ёу", "°").replace("ЁУ", "°")


def heading_prefix_for_word(roi_words, word):
    candidates = [
        item for item in roi_words
        if item.get("norm") == "HDG"
        and 0.0 < word["bbox"]["x_center"] - item["bbox"]["x_center"] <= 0.08
        and abs(word["bbox"]["y_center"] - item["bbox"]["y_center"]) <= 0.008
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: word["bbox"]["x_center"] - item["bbox"]["x_center"])


def add_text_boxes(chart_id, serial, selected_matches, lookup, detail_roi, existing_regions, roi_words=None):
    output = []
    roi_words = roi_words or []
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
        region_box = bbox(word["bbox"]["x_center"], word["bbox"]["y_center"], word["bbox"]["width"] * 1.12, word["bbox"]["height"] * 1.25)
        display_text = clean_pdf_display_text(word["text"])
        if rtype == "HEADING_TEXT":
            prefix = heading_prefix_for_word(roi_words, word)
            if prefix:
                region_box = bbox_union([prefix["bbox"], word["bbox"]], pad_x=0.003, pad_y=0.001) or region_box
                display_text = f"{clean_pdf_display_text(prefix['text'])} {display_text}"
        label = f"{rtype}: {display_text} -> {meta['expected_value']}"
        output.append(region(
            chart_id,
            serial,
            rtype,
            region_box,
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


def box_intersection_over_min(a, b):
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
    return inter / max(min(area_a, area_b), 1e-9)


def box_center_inside(inner, outer, pad=0.0):
    x0, y0, x1, y1 = box_edges(outer)
    cx = inner["x_center"]
    cy = inner["y_center"]
    return x0 - pad <= cx <= x1 + pad and y0 - pad <= cy <= y1 + pad


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


def normalize_region_label(item):
    labels = []
    for part in str(item.get("label") or "").split(";"):
        part = part.strip()
        if part and part not in labels:
            labels.append(part)
    region_type = item.get("region_type")
    if region_type == "CLIMB_ARROW":
        item["label"] = "curated lower detail: climb arrow" if any("curated lower detail" in label for label in labels) else "detected lower detail: climb arrow"
        return item
    if region_type == "FIX_SYMBOL":
        item["label"] = "detected lower detail: fix symbol"
        return item
    if region_type == "PATH_SEGMENT":
        item["label"] = "detected lower detail: path segment"
        return item
    if region_type == "HOLDING_PATTERN":
        item["label"] = "detected lower detail: holding pattern"
        return item
    if labels:
        item["label"] = "; ".join(labels)
    return item


def sanitize_region_mappings(item):
    normalize_region_label(item)
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


def add_all_present_mappings_to_coarse_regions(coarse_regions, lookup):
    for item in coarse_regions:
        region_type = item.get("region_type")
        if region_type not in {"MISSED_APPROACH_TEXT", "PLAN_VIEW"}:
            continue
        for key, meta in sorted(lookup.items()):
            basis = (
                "coarse MISSED_APPROACH_TEXT evidence region; human must verify whether this full text block supports the field"
                if region_type == "MISSED_APPROACH_TEXT"
                else "coarse PLAN_VIEW evidence region; human must verify whether this plan-view area supports the field"
            )
            confidence = 0.38 if region_type == "MISSED_APPROACH_TEXT" else 0.32
            add_mapping_if_missing(item, meta, basis, confidence)
        item["candidate_mappings"] = dedupe_mappings(item.get("candidate_mappings", []))
        apply_source_hint_from_mappings(item)
    return coarse_regions


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


def is_legacy_pilot_copy_region(item):
    return (
        item.get("source_layer") == "copied_from_reviewed_pilot10_prelabel"
        or "_pilotcopy_" in str(item.get("region_id") or "")
    )


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
    overlap_min = box_intersection_over_min(a["bbox"], b["bbox"])
    if iou >= 0.72 and a.get("region_type") == b.get("region_type"):
        return True
    if overlap_min >= 0.78 and a.get("region_type") == b.get("region_type"):
        return True
    if iou >= 0.78 and a.get("region_type") in TEXT_LIKE_TYPES and b.get("region_type") in TEXT_LIKE_TYPES:
        return True
    if (
        (iou >= 0.82 or overlap_min >= 0.86)
        and {a.get("region_type"), b.get("region_type")} <= {"FIX_SYMBOL", "HOLDING_PATTERN", "PATH_SEGMENT", "CLIMB_ARROW"}
    ):
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


def remove_text_overlapping_symbol_false_positives(regions, extra_text_regions=None):
    text_regions = [item for item in regions if item.get("region_type") in TEXT_LIKE_TYPES]
    text_regions.extend(extra_text_regions or [])
    output = []
    for item in regions:
        if item.get("region_type") != "FIX_SYMBOL":
            output.append(item)
            continue
        generated_symbol = (
            str(item.get("source_layer") or "") == "cv_icon_component"
            or "_iconalign_" in str(item.get("region_id") or "")
        )
        if not generated_symbol:
            output.append(item)
            continue
        overlaps_text = any(
            box_intersection_over_min(item["bbox"], text_item["bbox"]) >= 0.55
            or box_center_inside(item["bbox"], text_item["bbox"], pad=0.002)
            for text_item in text_regions
        )
        if not overlaps_text:
            output.append(item)
    return output


def remove_unmapped_fine_regions(regions):
    return [item for item in regions if item.get("candidate_mappings")]


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
    existing_fine = [
        item for item in prelabel.get("regions", [])
        if item.get("region_type") not in COARSE_TYPES
        and not is_legacy_pilot_copy_region(item)
    ]
    copied = adapt_pilot_regions(chart_id, lookup)

    pdf_path = FORMAL / "pdfs" / manifest_item["pdf_file"]
    image_path = resolve_workspace_path(manifest_item["image_path"])
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Source PDF is required for fine prelabels: {pdf_path}. "
            "Do not preserve/copy lower-detail boxes without the source PDF."
        )

    words = pdf_words(pdf_path)
    snap_coarse_regions_to_chart_boxes(coarse, image_path, words)
    add_all_present_mappings_to_coarse_regions(coarse, lookup)
    matches = word_matches(words, lookup)
    detail_roi, selected_matches = choose_detail_roi({"regions": coarse}, matches, image_path)
    plan_region = next((item for item in coarse if item.get("region_type") == "PLAN_VIEW"), None)
    plan_bottom = None
    if plan_region:
        plan_bottom = plan_region["bbox"]["y_center"] + plan_region["bbox"]["height"] / 2
    detail_roi, selected_matches = refine_detail_roi_to_lower_strip(image_path, detail_roi, selected_matches, strip_top_y=plan_bottom, all_matches=matches)
    clamp_plan_view_above_detail(coarse, detail_roi)
    detail_region = next((item for item in coarse if item.get("region_type") == "MISSED_APPROACH_DETAIL_AREA"), None)
    if detail_region:
        detail_region["bbox"] = detail_roi
        detail_region["label"] = "lower/profile missed-approach detail area snapped to AIP table lines"
        detail_region["source_layer"] = "pdf_text_cluster_icon_area_detector+lower_strip_line_refine"
        detail_region["confidence"] = 0.5 if selected_matches else 0.28

    serial = 1
    roi_words = [word for word in words if in_roi(word, detail_roi, pad=0.01)]
    text_regions, serial = add_text_boxes(chart_id, serial, selected_matches, lookup, detail_roi, copied, roi_words)
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
    pdf_word_regions = [{"bbox": word["bbox"]} for word in roi_words]
    all_fine = remove_text_overlapping_symbol_false_positives(all_fine, pdf_word_regions)
    all_fine = remove_unmapped_fine_regions(all_fine)
    all_fine = limit_duplicate_evidence(all_fine, detail_roi)
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
        "nested_duplicate_box_merge_enabled": True,
        "text_overlapping_symbol_false_positive_filter": True,
        "unmapped_fine_regions_removed": True,
        "all_present_fields_linked_to_coarse_ma_text_and_plan_view": True,
        "coarse_region_table_line_snap_enabled": True,
        "plan_view_long_line_snap_enabled": True,
        "lower_detail_edges_locked_to_detected_lines": True,
        "lower_detail_closed_cell_corner_required": True,
        "lower_detail_vertical_edge_cell_fallback_enabled": True,
        "lower_detail_connected_corner_required": True,
        "lower_detail_adjacent_cell_probe_enabled": True,
        "lower_detail_plan_overlap_guard_enabled": True,
        "lower_detail_runway_inset_clip_enabled": True,
        "practice10_pilot_copy_enabled": ENABLE_PRACTICE_PILOT_COPY,
        "low_confidence_blank_fallback_boxes_enabled": ENABLE_LOW_CONFIDENCE_FALLBACK_BOXES,
        "source_pdfs_available": True,
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
    if REQUIRE_SOURCE_PDFS_FOR_FINE_PRELABELS:
        missing_pdfs = [FORMAL / "pdfs" / item["pdf_file"] for item in manifest if not (FORMAL / "pdfs" / item["pdf_file"]).exists()]
        if missing_pdfs:
            examples = "\n".join(f"  - {path}" for path in missing_pdfs[:10])
            extra = "" if len(missing_pdfs) <= 10 else f"\n  ... and {len(missing_pdfs) - 10} more"
            raise SystemExit(
                "Missing source PDFs for formal300 fine prelabel generation.\n"
                "Put the PDFs under annotation_tools/shujuji_annotation/datasets/formal300/pdfs/ "
                "using the filenames from manifest.json, then rerun.\n"
                f"Missing count: {len(missing_pdfs)}\n{examples}{extra}"
            )
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
