from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "benchmark_exports" / "derived" / "v2" / "pilot10_external"
SCHEMA_PATH = ROOT / "schemas" / "missed_approach_leg.schema.json"
RUN_OUTPUT_ROOT = ROOT / "predictions" / "pilot10_external"
DEFAULT_OCR_TEXT_ROOT = ROOT / "ocr_artifacts" / "pilot10_external" / "ocr1_paddleocr_ppocrv5_20260428_r1" / "full_text"
sys.path.insert(0, str(ROOT / "scripts"))

from run_pilot10_anthropic import (
    fill_prompt,
    read_jsonl,
    resolve_package_path,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)
from model_clients import call_model_json, create_model_client, model_api_manifest, save_model_response


DEFAULT_RUN_ID = "pilot10_group1_ocr1_b1prime_c4_gpt54_20260428_r1"

B1_PRIME_PROMPT = ROOT / "prompts" / "paper_v2" / "b1_prime_ocr_field_candidates_to_canonical_pilot10.zh_v0_candidate.md"
C4_PROMPT = ROOT / "prompts" / "paper_v2" / "c4_image_ocr_to_canonical_pilot10.zh_v1_candidate.md"
FIELD_CANDIDATES_SCHEMA = ROOT / "schemas" / "field_candidates.schema.candidate.json"

STOPWORDS = {
    "ABLE",
    "ABOVE",
    "AFTER",
    "AIRPORT",
    "ALTERNATE",
    "AND",
    "APP",
    "APCH",
    "APPR",
    "APPROACH",
    "AT",
    "BELOW",
    "CLIMB",
    "CONTINUE",
    "COURSE",
    "DEPARTURE",
    "DIRECT",
    "DME",
    "FINAL",
    "FIX",
    "FROM",
    "HEADING",
    "HDG",
    "HOLD",
    "HOLDING",
    "ILS",
    "LEFT",
    "LOCALIZER",
    "MISSED",
    "NAVAID",
    "NDB",
    "NM",
    "PROC",
    "PROCEDURE",
    "RADAR",
    "RADIAL",
    "RIGHT",
    "RNAV",
    "RNP",
    "ROUTE",
    "RUNWAY",
    "THEN",
    "THE",
    "TO",
    "TURN",
    "VOR",
    "VORTAC",
    "WAYPOINT",
    "CITY",
    "DOES",
    "APPLY",
    "EAST",
    "FIELD",
    "LAKE",
    "LOM",
    "NAS",
    "PER",
    "WEST",
    "AL",
    "APR",
    "APT",
    "ASOS",
    "CANADA",
    "CAT",
    "COUNTY",
    "CRS",
    "CTAF",
    "ELEV",
    "FAA",
    "GPS",
    "HIRL",
    "IDG",
    "MAY",
    "MIRL",
    "MSA",
    "NEW",
    "NIGHT",
    "OCR",
    "ORIG",
    "REIL",
    "STATES",
    "TDZE",
    "UNICOM",
    "UNITED",
    "VISUAL",
    "YORK",
    "ALL",
    "ALS",
    "ALSF",
    "ANGLE",
    "ANGLES",
    "ATIS",
    "AWOS",
    "BARO",
    "BOUND",
    "CENTER",
    "CHAN",
    "CLNC",
    "CON",
    "CATS",
    "DEL",
    "DURING",
    "ENTRY",
    "EXCEED",
    "FAF",
    "FEET",
    "FLD",
    "FOR",
    "GND",
    "IAF",
    "INOP",
    "INT",
    "INTL",
    "LAST",
    "LDG",
    "LNAV",
    "LOC",
    "LOCAL",
    "LPV",
    "MALS",
    "MALSF",
    "MALSR",
    "MAP",
    "MDA",
    "MDAS",
    "MEML",
    "MIN",
    "MINUTE",
    "MILE",
    "NOT",
    "NOPT",
    "NORTH",
    "ONE",
    "PAA",
    "PPA",
    "REMAIN",
    "RGNL",
    "RVR",
    "SOUTH",
    "SNA",
    "TABLE",
    "TCH",
    "TOWER",
    "TRACK",
    "TWR",
    "UNTIL",
    "USE",
    "USING",
    "VDP",
    "VIA",
    "VGSI",
    "VNAV",
    "WAAS",
    "WHEN",
    "WITH",
}

FREQUENCY_OR_COMM_WORDS = {
    "APP CON",
    "ATIS",
    "AWOS",
    "ASOS",
    "CTAF",
    "GND CON",
    "TOWER",
    "UNICOM",
}

PROCEDURAL_CONTEXT_WORDS = {
    "CLIMB",
    "COURSE",
    "DIRECT",
    "HEADING",
    "HDG",
    "HOLD",
    "HOLDING",
    "MAINTAIN",
    "RADIAL",
    "TRACK",
    "VIA",
    "VOR/DME",
}

DEGREE_MARK = r"(?:DEG|DEGREES|[°º˚掳])"
TRACK_TO_FIX_RE = re.compile(
    rf"\b(?:ON\s+)?(?:TRACK|TRK|COURSE|CRS|HEADING|HDG|RADIAL|R-)?\s*"
    rf"([0-3]?[0-9]{{2}})\s*{DEGREE_MARK}?\s+TO\s+([A-Z][A-Z0-9]{{2,5}})\b",
    flags=re.IGNORECASE,
)

SOURCE_SECTION_RANK = {
    "missed_approach_text": 0,
    "plan_view": 1,
    "profile_view": 1,
    "briefing_strip": 2,
    "full_chart_unknown": 3,
    "unknown": 4,
}

INSTRUCTION_BOUNDARY_RE = re.compile(
    r"\b(?:"
    r"D-?ATIS|ATIS|AWOS|ASOS|UNICOM|GND\s+CON|TOWER|APP\s+CON|CTAF|"
    r"Apt\s+Elev|TDZE|TCH|MIRL|REIL|HIRL|MALSR|ALSF|"
    r"NOTE:|NOTES:|CHART|PROFILE|LOCALIZER|MISSED\s+APCH\s+FIX|ALTERNATE\s+MISSED"
    r")\b",
    flags=re.IGNORECASE,
)

INSTRUCTION_START_RE = re.compile(
    r"\b(?:CLIMB|CONTINUE|WHEN\s+DIRECTED|PROCEED|FLY|TURN)\b",
    flags=re.IGNORECASE,
)


def unique_in_order(values: list[Any], limit: int = 50) -> list[Any]:
    seen = set()
    output = []
    for value in values:
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
        if len(output) >= limit:
            break
    return output


def snippet_around(text: str, start: int, end: int, window: int = 60) -> str:
    snippet_start = max(start - window, 0)
    snippet_end = min(end + window, len(text))
    return re.sub(r"\s+", " ", text[snippet_start:snippet_end]).strip()


def infer_source_section(snippet: str) -> str:
    upper = snippet.upper()
    if "PROFILE" in upper or "VGSI" in upper:
        return "profile_view"
    if "PLANVIEW" in upper or "PLAN VIEW" in upper:
        return "plan_view"
    if "BRIEFING" in upper:
        return "briefing_strip"
    return "full_chart_unknown"


def compact_ocr_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def missed_approach_heading_is_procedure(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 32) : match.start()].upper()
    suffix = text[match.end() : min(len(text), match.end() + 24)].upper()
    return "ALTERNATE" not in prefix and not suffix.lstrip().startswith("FIX")


def instruction_end_offset(local_text: str) -> int:
    for boundary in INSTRUCTION_BOUNDARY_RE.finditer(local_text):
        if boundary.start() >= 90:
            return boundary.start()
    return len(local_text)


def missed_approach_instruction_candidates(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"\bMISSED\s+(?:APPROACH|APCH)\b:?", text, flags=re.IGNORECASE):
        if not missed_approach_heading_is_procedure(text, match):
            continue
        search_start = match.end()
        search_end = min(len(text), search_start + 900)
        post_heading = text[search_start:search_end]
        instruction_start = match.start()
        start_match = INSTRUCTION_START_RE.search(post_heading)
        if start_match and start_match.start() <= 220:
            instruction_start = search_start + start_match.start()
        local = text[instruction_start:search_end]
        end = instruction_start + instruction_end_offset(local)
        end = min(end, instruction_start + 700)
        value = compact_ocr_text(text[instruction_start:end])
        if len(value) < 20:
            continue
        candidates.append(
            {
                "value": value,
                "field_type": "missed_approach_instruction",
                "source": "ocr_text",
                "source_section": "missed_approach_text",
                "source_snippet": value,
                "source_start_char": instruction_start,
                "source_end_char": end,
                "rule_id": "missed_approach_instruction_span_regex_v8",
                "confidence": 0.95,
                "notes": "continuous_ocr_only_missed_approach_instruction_span_no_target_or_field_to_leg_linking",
            }
        )
    return unique_in_order(candidates, limit=4)


def missed_approach_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for candidate in missed_approach_instruction_candidates(text):
        start = candidate.get("source_start_char")
        end = candidate.get("source_end_char")
        if isinstance(start, int) and isinstance(end, int):
            spans.append((start, end))
    return spans


def section_for_position(start: int | None, end: int | None, spans: list[tuple[int, int]], snippet: str) -> str:
    if start is not None and end is not None:
        for span_start, span_end in spans:
            if start >= span_start and end <= span_end:
                return "missed_approach_text"
    return infer_source_section(snippet)


def make_candidate(
    *,
    value: str | int | float | bool,
    field_type: str,
    text: str,
    start: int | None,
    end: int | None,
    rule_id: str,
    window: int = 60,
    ma_spans: list[tuple[int, int]] | None = None,
    confidence: float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    source_snippet = snippet_around(text, start, end, window=window) if start is not None and end is not None else ""
    source_section = section_for_position(start, end, ma_spans or [], source_snippet)
    return {
        "value": value,
        "field_type": field_type,
        "source": "ocr_text",
        "source_section": source_section,
        "source_snippet": source_snippet,
        "source_start_char": start,
        "source_end_char": end,
        "rule_id": rule_id,
        "confidence": confidence,
        "notes": notes,
    }


def context_has_any(snippet: str, words: set[str]) -> bool:
    upper = snippet.upper()
    return any(word in upper for word in words)


def is_likely_frequency_or_comm(snippet: str) -> bool:
    upper = snippet.upper()
    if context_has_any(upper, {"CLIMB", "DIRECT", "HOLD", "HOLDING", "MISSED APPROACH", "MISSED APCH"}):
        return False
    if context_has_any(upper, FREQUENCY_OR_COMM_WORDS):
        return True
    return bool(re.search(r"\b(?:1[0-3][0-9]\.\d|2[0-9]{2}\.\d)\b", upper))


def is_obvious_date_or_chart_artifact(value: int, snippet: str) -> bool:
    upper = snippet.upper()
    if value in {2026, 2025, 2024} and re.search(r"\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", upper):
        return True
    if re.search(r"\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", upper):
        return True
    if re.search(r"\b\d{2,3}掳\d{2}'?[NSEW]\b", upper):
        return True
    return False


def has_heading_or_radial_context_near(text: str, start: int, end: int) -> bool:
    nearby = snippet_around(text, start, end, window=28).upper()
    return bool(re.search(r"\b(?:HEADING|HDG|RADIAL|R-|COURSE|CRS|TRACK|BEARING)\b", nearby))


def candidate_quality(field_type: str, source_section: str, snippet: str) -> tuple[float, str]:
    if field_type == "missed_approach_instruction":
        return 0.95, "continuous_missed_approach_instruction_span"
    if field_type == "track_to_fix_phrase":
        return 0.82, "flat_ocr_track_to_fix_phrase_no_leg_binding"
    if field_type == "route_sequence_snippet":
        return 0.72, "flat_ocr_route_sequence_snippet_no_leg_binding"
    procedural = context_has_any(snippet, PROCEDURAL_CONTEXT_WORDS)
    if source_section == "missed_approach_text" and procedural:
        return 0.9, "high_precision_missed_approach_procedure_context"
    if source_section == "missed_approach_text":
        return 0.65, "missed_approach_span_weak_context"
    if procedural:
        return 0.45, "other_chart_text_procedure_word_context"
    return 0.25, "weak_other_chart_text_candidate"


def with_quality(candidate: dict[str, Any]) -> dict[str, Any]:
    confidence, notes = candidate_quality(
        str(candidate.get("field_type") or ""),
        str(candidate.get("source_section") or ""),
        str(candidate.get("source_snippet") or ""),
    )
    candidate["confidence"] = confidence
    candidate["notes"] = notes
    return candidate


def phrase_candidates(
    text: str,
    pattern: str,
    *,
    field_type: str,
    rule_id: str,
    ma_spans: list[tuple[int, int]] | None = None,
    window: int = 80,
    limit: int = 20,
) -> list[dict[str, Any]]:
    candidates = []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        snippet = snippet_around(text, match.start(), match.end(), window=window)
        candidates.append(
            {
                "value": snippet,
                "field_type": field_type,
                "source": "ocr_text",
                "source_section": section_for_position(match.start(), match.end(), ma_spans or [], snippet),
                "source_snippet": snippet,
                "source_start_char": match.start(),
                "source_end_char": match.end(),
                "rule_id": rule_id,
                "confidence": None,
                "notes": None,
            }
        )
    return unique_in_order(candidates, limit=limit)


def track_to_fix_phrase_candidates(text: str, ma_spans: list[tuple[int, int]]) -> list[dict[str, Any]]:
    candidates = []
    for match in TRACK_TO_FIX_RE.finditer(text):
        fix = match.group(2).upper()
        if fix in STOPWORDS or fix.startswith("RW") or re.fullmatch(r"[O0][0-9]{2,3}", fix):
            continue
        snippet = snippet_around(text, match.start(), match.end(), window=70)
        candidates.append(
            {
                "value": compact_ocr_text(match.group(0)),
                "field_type": "track_to_fix_phrase",
                "source": "ocr_text",
                "source_section": section_for_position(match.start(), match.end(), ma_spans, snippet),
                "source_snippet": snippet,
                "source_start_char": match.start(),
                "source_end_char": match.end(),
                "rule_id": "track_to_fix_phrase_regex_v8",
                "confidence": None,
                "notes": None,
            }
        )
    return unique_in_order(candidates, limit=24)


def route_sequence_snippet_candidates(text: str, ma_spans: list[tuple[int, int]]) -> list[dict[str, Any]]:
    candidates = []
    for match in re.finditer(r"\bTR\s+TR\b|\bTRACK\b|[°º˚掳]", text, flags=re.IGNORECASE):
        snippet_start = max(0, match.start() - 140)
        snippet_end = min(len(text), match.end() + 220)
        snippet = compact_ocr_text(text[snippet_start:snippet_end])
        upper = snippet.upper()
        tokens = [
            token
            for token in re.findall(r"\b[A-Z][A-Z0-9]{2,5}\b", upper)
            if token not in STOPWORDS and not token.startswith("RW") and not re.fullmatch(r"[O0][0-9]{2,3}", token)
        ]
        degree_count = len(re.findall(rf"\b[0-3]?[0-9]{{2}}\s*{DEGREE_MARK}", upper, flags=re.IGNORECASE))
        if len(set(tokens)) < 3 or degree_count < 2:
            continue
        candidates.append(
            {
                "value": snippet,
                "field_type": "route_sequence_snippet",
                "source": "ocr_text",
                "source_section": section_for_position(snippet_start, snippet_end, ma_spans, snippet),
                "source_snippet": snippet,
                "source_start_char": snippet_start,
                "source_end_char": snippet_end,
                "rule_id": "route_sequence_snippet_regex_v8",
                "confidence": None,
                "notes": None,
            }
        )
    return unique_in_order(candidates, limit=8)


def candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, float, int, str]:
    section = candidate.get("source_section") or "unknown"
    start = candidate.get("source_start_char")
    confidence = candidate.get("confidence")
    return (
        SOURCE_SECTION_RANK.get(section, 9),
        -(confidence if isinstance(confidence, (int, float)) else 0),
        start if isinstance(start, int) else 10**9,
        str(candidate.get("value")),
    )


def sorted_unique_candidates(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return unique_in_order(sorted(candidates, key=candidate_sort_key), limit=limit)


def sorted_unique_candidates_by_section(
    candidates: list[dict[str, Any]],
    *,
    total_limit: int,
    section_limits: dict[str, int],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    section_counts: dict[str, int] = {}
    for candidate in sorted(candidates, key=candidate_sort_key):
        section = candidate.get("source_section") or "unknown"
        if section_counts.get(section, 0) >= section_limits.get(section, total_limit):
            continue
        selected.append(candidate)
        section_counts[section] = section_counts.get(section, 0) + 1
        if len(selected) >= total_limit:
            break
    return unique_in_order(selected, limit=total_limit)


def build_field_candidates(ocr_text: str, chart_id: str) -> dict[str, Any]:
    upper = ocr_text.upper()
    ma_spans = missed_approach_spans(ocr_text)
    instruction_snippets = missed_approach_instruction_candidates(ocr_text)

    fix_candidates = []
    for match in re.finditer(r"\b[A-Z][A-Z0-9]{2,5}\b", upper):
        token = match.group(0)
        if len(token) > 5 or token in STOPWORDS or token.startswith("RW") or token.isdigit():
            continue
        if re.fullmatch(r"[O0][0-9]{2,3}", token):
            continue
        candidate = make_candidate(
            value=token,
            field_type="fix_ident",
            text=ocr_text,
            start=match.start(),
            end=match.end(),
            rule_id="fix_ident_token_regex_v8",
            ma_spans=ma_spans,
        )
        if is_likely_frequency_or_comm(candidate["source_snippet"]):
            continue
        if candidate["source_section"] == "full_chart_unknown" and not context_has_any(
            candidate["source_snippet"], {"DIRECT", "HOLD", "HOLDING", "MISSED APCH FIX", "R-", "VOR/DME"}
        ):
            continue
        fix_candidates.append(with_quality(candidate))

    for match in re.finditer(r"\b(?:RWY|RUNWAY)\s*([0-3]?[0-9][LCR]?)\b", upper):
        candidate = make_candidate(
            value=f"RW{match.group(1)}",
            field_type="runway_ident",
            text=ocr_text,
            start=match.start(),
            end=match.end(),
            rule_id="runway_ident_regex_v8",
            ma_spans=ma_spans,
        )
        fix_candidates.append(with_quality(candidate))

    altitude_candidates = []
    for match in re.finditer(r"(?<![\dO.])([1-9][0-9O]{2,4})(?![\dO.])", upper):
        value = int(match.group(1).replace("O", "0"))
        if 300 <= value <= 18000:
            candidate = make_candidate(
                value=value,
                field_type="altitude_ft",
                text=ocr_text,
                start=match.start(),
                end=match.end(),
                rule_id="altitude_ft_regex_v8",
                ma_spans=ma_spans,
            )
            snippet = candidate["source_snippet"]
            if is_likely_frequency_or_comm(snippet) or is_obvious_date_or_chart_artifact(value, snippet):
                continue
            if (
                300 <= value <= 360
                and (
                    has_heading_or_radial_context_near(ocr_text, match.start(1), match.end(1))
                    or re.match(rf"\s*{DEGREE_MARK}", upper[match.end(1) : match.end(1) + 8], flags=re.IGNORECASE)
                )
            ):
                continue
            if candidate["source_section"] != "missed_approach_text" and not context_has_any(
                snippet, {"CLIMB", "MAINTAIN", "CROSS", "ALTITUDE"}
            ):
                continue
            altitude_candidates.append(with_quality(candidate))

    turn_candidates = []
    for match in re.finditer(r"\bLEFT\b|\bLT\b", upper):
        candidate = make_candidate(
            value="LEFT",
            field_type="turn_direction",
            text=ocr_text,
            start=match.start(),
            end=match.end(),
            rule_id="turn_direction_regex_v8",
            ma_spans=ma_spans,
        )
        turn_candidates.append(with_quality(candidate))
    for match in re.finditer(r"\bRIGHT\b|\bRT\b", upper):
        candidate = make_candidate(
            value="RIGHT",
            field_type="turn_direction",
            text=ocr_text,
            start=match.start(),
            end=match.end(),
            rule_id="turn_direction_regex_v8",
            ma_spans=ma_spans,
        )
        turn_candidates.append(with_quality(candidate))

    course_candidates = []
    for match in re.finditer(
        r"\b(?:COURSE|CRS|HEADING|HDG|RADIAL|R-|TRACK|BEARING)\s*([0-3][0-9]{2})\b",
        upper,
    ):
        value = int(match.group(1))
        if 1 <= value <= 360:
            matched_text = match.group(0)
            if "RADIAL" in matched_text or "R-" in matched_text:
                field_type = "radial_deg"
            elif "HEADING" in matched_text or "HDG" in matched_text:
                field_type = "heading_deg"
            else:
                field_type = "course_deg"
            candidate = make_candidate(
                value=value,
                field_type=field_type,
                text=ocr_text,
                start=match.start(1),
                end=match.end(1),
                rule_id="course_heading_radial_regex_v8",
                ma_spans=ma_spans,
            )
            course_candidates.append(with_quality(candidate))
    for match in re.finditer(rf"\b([0-3]?[0-9]{{2}})\s*{DEGREE_MARK}(?=\s|$|[),.;:])", upper, flags=re.IGNORECASE):
        value = int(match.group(1))
        if 1 <= value <= 360:
            candidate = make_candidate(
                value=value,
                field_type="course_deg",
                text=ocr_text,
                start=match.start(1),
                end=match.end(1),
                rule_id="degree_value_regex_v8",
                ma_spans=ma_spans,
            )
            if candidate["source_section"] != "missed_approach_text" and not context_has_any(
                candidate["source_snippet"], {"COURSE", "HEADING", "HDG", "RADIAL", "TRACK", "R-"}
            ):
                continue
            course_candidates.append(with_quality(candidate))

    track_to_fix_snippets = [with_quality(item) for item in track_to_fix_phrase_candidates(ocr_text, ma_spans)]
    route_sequence_snippets = [with_quality(item) for item in route_sequence_snippet_candidates(ocr_text, ma_spans)]

    hold_candidates = [with_quality(item) for item in phrase_candidates(
        ocr_text,
        r"\bHOLD(?:ING)?\b",
        field_type="hold_phrase",
        rule_id="hold_phrase_regex_v8",
        ma_spans=ma_spans,
        window=80,
        limit=20,
    )]
    direct_snippets = [with_quality(item) for item in phrase_candidates(
        ocr_text,
        r"\bDIRECT\b",
        field_type="direct_phrase",
        rule_id="direct_phrase_regex_v8",
        ma_spans=ma_spans,
        window=80,
        limit=20,
    )]
    climb_snippets = [with_quality(item) for item in phrase_candidates(
        ocr_text,
        r"\bCLIMB\b",
        field_type="climb_phrase",
        rule_id="climb_phrase_regex_v8",
        ma_spans=ma_spans,
        window=80,
        limit=20,
    )]

    return {
        "schema_version": "field_candidates_schema_v1_candidate",
        "chart_id": chart_id,
        "candidate_source": "ocr_text_only_regex_field_matcher_pilot_v8",
        "source_contract": {
            "source": "same_chart_full_chart_ocr_text",
            "allows_ocr_bbox": False,
            "allows_chart_image_pixels": False,
        },
        "leakage_policy": {
            "uses_canonical_target": False,
            "uses_expected_value": False,
            "uses_gold_field_to_leg_mapping": False,
            "uses_human_evidence_provenance": False,
            "uses_gold_observable_evidence": False,
            "uses_cifp_or_arinc_424": False,
            "uses_scorer_output": False,
        },
        "field_candidates": {
            "fix_candidates": sorted_unique_candidates_by_section(
                fix_candidates,
                total_limit=24,
                section_limits={
                    "missed_approach_text": 18,
                    "plan_view": 3,
                    "profile_view": 3,
                    "briefing_strip": 4,
                    "full_chart_unknown": 4,
                    "unknown": 2,
                },
            ),
            "altitude_candidates": sorted_unique_candidates_by_section(
                altitude_candidates,
                total_limit=18,
                section_limits={
                    "missed_approach_text": 14,
                    "plan_view": 3,
                    "profile_view": 3,
                    "briefing_strip": 4,
                    "full_chart_unknown": 3,
                    "unknown": 2,
                },
            ),
            "turn_candidates": sorted_unique_candidates(turn_candidates, limit=4),
            "course_candidates": sorted_unique_candidates_by_section(
                course_candidates,
                total_limit=16,
                section_limits={
                    "missed_approach_text": 10,
                    "plan_view": 3,
                    "profile_view": 3,
                    "briefing_strip": 4,
                    "full_chart_unknown": 3,
                    "unknown": 2,
                },
            ),
            "hold_candidates": sorted_unique_candidates(hold_candidates, limit=12),
            "instruction_snippets": sorted_unique_candidates(instruction_snippets, limit=4),
            "track_to_fix_snippets": sorted_unique_candidates(track_to_fix_snippets, limit=12),
            "route_sequence_snippets": sorted_unique_candidates(route_sequence_snippets, limit=3),
            "direct_phrase_snippets": sorted_unique_candidates(direct_snippets, limit=10),
            "climb_phrase_snippets": sorted_unique_candidates(climb_snippets, limit=10),
        },
    }


def call_model_json_prefill(
    client: Any,
    *,
    provider: str,
    model: str,
    prompt: str,
    image_path: Path | None,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    assistant_prefill_json: bool,
) -> tuple[str, Any]:
    return call_model_json(
        client,
        provider=provider,
        model=model,
        prompt=prompt,
        image_path=image_path,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        assistant_prefill_json=assistant_prefill_json,
    )


def parse_strict_json(text: str) -> tuple[dict[str, Any], str]:
    return json.loads(text.strip()), "strict_json"


def summarize_method(method: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    method_results = [item for item in results if item["method"] == method]
    scored = [item["score"] for item in method_results if item.get("score")]
    correct = sum(item["correct"] for item in scored)
    total = sum(item["total"] for item in scored)
    policy_counts: dict[str, int] = {}
    for item in method_results:
        policy = item.get("json_extraction_policy") or "failed"
        policy_counts[policy] = policy_counts.get(policy, 0) + 1
    non_strict_count = sum(count for policy, count in policy_counts.items() if policy != "strict_json")
    return {
        "samples_total": len(method_results),
        "schema_valid": sum(1 for item in method_results if item.get("validation_error_count") == 0),
        "samples_scored": len(scored),
        "json_extraction_policy_counts": policy_counts,
        "parser_repair_count_non_strict_json": non_strict_count,
        "score": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        },
        "results": method_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1_prime and C4 on pilot10 with strict JSON prefill.")
    parser.add_argument("--provider", default="openai_compatible", choices=["openai_compatible", "anthropic_compatible"])
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens-b1-prime", type=int, default=4096)
    parser.add_argument("--max-tokens-c4", type=int, default=4096)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--ocr-text-root", type=Path, default=DEFAULT_OCR_TEXT_ROOT)
    parser.add_argument("--json-mode", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--assistant-prefill-json", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dir = RUN_OUTPUT_ROOT / args.run_id
    if run_dir.exists() and not args.dry_run:
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    manifest_path = DATA_DIR / "pilot10_manifest.jsonl"
    rows = read_jsonl(manifest_path)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    ocr_source_dir = args.ocr_text_root

    run_manifest = {
        "run_id": args.run_id,
        "method_ids": ["B1_prime", "C4"],
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "sample_role": "pilot10_external_excluded_from_formal_evaluation",
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": {
            "b1_prime": args.max_tokens_b1_prime,
            "c4": args.max_tokens_c4,
        },
        "api": model_api_manifest(
            provider=args.provider,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            json_mode=args.json_mode,
            assistant_prefill_json=args.assistant_prefill_json,
        ),
        "reused_frozen_or_prefrozen_assets": {
            "schema": {
                "path": str(SCHEMA_PATH.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(SCHEMA_PATH),
                "status": "frozen_canonical_json_contract_v1",
            },
            "parser_policy": {
                "strict_json_only": True,
                "json_mode": args.json_mode,
                "assistant_prefill_json": args.assistant_prefill_json,
                "assistant_prefill_value": "{" if args.assistant_prefill_json else None,
                "semantic_repair": False,
                "code_fence_stripping_allowed": False,
            },
            "ocr_artifact_source_for_pilot": str(ocr_source_dir.relative_to(ROOT)).replace("\\", "/"),
            "ocr_id": "OCR-1",
            "ocr_source_policy": "ordinary_ocr_not_mllm_transcription",
        },
        "new_temporary_prefreeze_required": {
            "B1_prime_field_candidates_schema": "field_candidates_schema_v1_candidate",
            "B1_prime_field_matcher_rules": "pilot_candidate_regex_ocr_text_only_v8",
            "C4_allowed_forbidden_inputs": "pilot_candidate",
            "B1_prime_prompt": "candidate_not_frozen",
            "C4_prompt": "candidate_not_frozen",
            "formal_note": "This corrected run must use ordinary OCR-1, not Claude/MLLM OCR text.",
        },
        "field_candidates_schema": {
            "path": str(FIELD_CANDIDATES_SCHEMA.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(FIELD_CANDIDATES_SCHEMA),
            "status": "candidate_not_frozen",
            "format": "object_candidates_not_field_to_leg_linking",
        },
        "prompts": {
            "b1_prime": {
                "path": str(B1_PRIME_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(B1_PRIME_PROMPT),
            },
            "c4": {
                "path": str(C4_PROMPT.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(C4_PROMPT),
            },
        },
        "field_matcher": {
            "path": "scripts/run_b1prime_c4_pilot10.py",
            "function": "build_field_candidates",
            "sha256": sha256_file(Path(__file__)),
            "uses_target": False,
            "uses_expected_value": False,
            "uses_gold_field_to_leg_mapping": False,
            "uses_human_evidence_provenance": False,
            "uses_gold_observable_evidence": False,
            "uses_cifp_or_arinc_424": False,
            "uses_scorer_output": False,
        },
        "scoring": {
            "target_used_only_after_validation": True,
            "target_source": "pilot10_external canonical_proxy_gt_file",
        },
        "samples": [row["pilot_sample_id"] for row in rows],
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    if args.dry_run:
        print(f"Dry run prepared {len(rows)} samples in {run_dir}.")
        return 0

    client = create_model_client(provider=args.provider, base_url=args.base_url, api_key_env=args.api_key_env)
    b1_prime_template = B1_PRIME_PROMPT.read_text(encoding="utf-8")
    c4_template = C4_PROMPT.read_text(encoding="utf-8")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for row in rows:
        sample_id = row["pilot_sample_id"]
        chart_id = row["chart_id"]
        image_path = resolve_package_path(row["image_path"])
        target_path = resolve_package_path(row["canonical_proxy_gt_file"])
        target = json.loads(target_path.read_text(encoding="utf-8"))
        ocr_text_path = ocr_source_dir / f"{chart_id}.txt"

        print(f"Running B1_prime/C4 {sample_id} {chart_id}", flush=True)

        if not ocr_text_path.exists():
            error = f"missing_ocr_text:{ocr_text_path.relative_to(ROOT).as_posix()}"
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "method": "OCR_SOURCE", "error": error})
            continue

        ocr_text = ocr_text_path.read_text(encoding="utf-8")
        field_candidates = build_field_candidates(ocr_text, chart_id)
        write_json(run_dir / "B1_prime" / "field_candidates" / f"{chart_id}.json", field_candidates)

        try:
            prompt = fill_prompt(b1_prime_template, row, ocr_text=ocr_text)
            prompt = prompt.replace(
                "{{field_candidates_json}}",
                json.dumps(field_candidates, ensure_ascii=False, indent=2),
            )
            text, response = call_model_json_prefill(
                client,
                provider=args.provider,
                model=args.model,
                prompt=prompt,
                image_path=None,
                max_tokens=args.max_tokens_b1_prime,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
            )
            write_text(run_dir / "B1_prime" / "raw_text" / f"{chart_id}.txt", text)
            save_model_response(run_dir / "B1_prime" / "raw_responses" / f"{chart_id}.json", response)
            pred, extraction_policy = parse_strict_json(text)
            write_json(run_dir / "B1_prime" / "canonical_json" / f"{chart_id}.json", pred)
            validation_errors = validate_canonical(pred, validator)
            write_json(run_dir / "B1_prime" / "validation" / f"{chart_id}.json", validation_errors)
            item: dict[str, Any] = {
                "method": "B1_prime",
                "sample_id": sample_id,
                "chart_id": chart_id,
                "json_extraction_policy": extraction_policy,
                "validation_error_count": len(validation_errors),
                "validation_errors": validation_errors,
                "score": None,
            }
            if not validation_errors:
                score = score_canonical(pred, target)
                write_json(run_dir / "B1_prime" / "scores" / f"{chart_id}.json", score)
                item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
            else:
                failures.append(
                    {
                        "sample_id": sample_id,
                        "chart_id": chart_id,
                        "method": "B1_prime",
                        "error": "schema_validation_failed",
                    }
                )
            results.append(item)
        except Exception as exc:
            write_text(run_dir / "B1_prime" / "parse_errors" / f"{chart_id}.txt", repr(exc))
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "method": "B1_prime", "error": repr(exc)})
            results.append(
                {
                    "method": "B1_prime",
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "json_extraction_policy": None,
                    "validation_error_count": None,
                    "validation_errors": None,
                    "score": None,
                    "failure": repr(exc),
                }
            )

        try:
            prompt = fill_prompt(c4_template, row, ocr_text=ocr_text)
            text, response = call_model_json_prefill(
                client,
                provider=args.provider,
                model=args.model,
                prompt=prompt,
                image_path=image_path,
                max_tokens=args.max_tokens_c4,
                temperature=args.temperature,
                json_mode=args.json_mode,
                assistant_prefill_json=args.assistant_prefill_json,
            )
            write_text(run_dir / "C4" / "raw_text" / f"{chart_id}.txt", text)
            save_model_response(run_dir / "C4" / "raw_responses" / f"{chart_id}.json", response)
            pred, extraction_policy = parse_strict_json(text)
            write_json(run_dir / "C4" / "canonical_json" / f"{chart_id}.json", pred)
            validation_errors = validate_canonical(pred, validator)
            write_json(run_dir / "C4" / "validation" / f"{chart_id}.json", validation_errors)
            item = {
                "method": "C4",
                "sample_id": sample_id,
                "chart_id": chart_id,
                "json_extraction_policy": extraction_policy,
                "validation_error_count": len(validation_errors),
                "validation_errors": validation_errors,
                "score": None,
            }
            if not validation_errors:
                score = score_canonical(pred, target)
                write_json(run_dir / "C4" / "scores" / f"{chart_id}.json", score)
                item["score"] = {key: score[key] for key in ["correct", "total", "accuracy"]}
            else:
                failures.append(
                    {"sample_id": sample_id, "chart_id": chart_id, "method": "C4", "error": "schema_validation_failed"}
                )
            results.append(item)
        except Exception as exc:
            write_text(run_dir / "C4" / "parse_errors" / f"{chart_id}.txt", repr(exc))
            failures.append({"sample_id": sample_id, "chart_id": chart_id, "method": "C4", "error": repr(exc)})
            results.append(
                {
                    "method": "C4",
                    "sample_id": sample_id,
                    "chart_id": chart_id,
                    "json_extraction_policy": None,
                    "validation_error_count": None,
                    "validation_errors": None,
                    "score": None,
                    "failure": repr(exc),
                }
            )

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "parameter_status": "temporary_pilot_use_only_not_final_freeze",
        "methods": {
            "B1_prime": summarize_method("B1_prime", results),
            "C4": summarize_method("C4", results),
        },
        "failures": failures,
    }
    write_json(run_dir / "summary_report.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
