from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema


SCHEMA_VERSION = "field_to_leg_links_schema_v0_candidate"
LINK_SOURCE = "ocr_text_only_field_to_leg_linker_v2_candidate"
BAD_FIX_TOKENS = {
    "AND",
    "THE",
    "HOLD",
    "HOLDING",
    "PATTERN",
    "MINUTE",
    "ONE",
    "NA",
    "NIGHT",
    "RNP",
    "GPS",
    "RWY",
    "VOR",
    "DME",
    "VORTAC",
    "NDB",
    "TACAN",
    "LOC",
    "INT",
    "LOM",
    "FEET",
    "TRACK",
    "COURSE",
}
FACILITY_DESCRIPTOR_RE = r"(?:VORTAC|VOR/DME|VOR|DME|NDB|TACAN|LOC|INT|LOM)"
RUNWAY_FIX_RE = re.compile(r"^(?:RW|RWY)\d{1,2}[LRC]?$", re.IGNORECASE)

COURSE_TO_FIX_RE = re.compile(
    r"(?:(?:on\s+)?(?:track|course|heading|radial)\s+)?"
    r"(?P<course>\d{2,3})\s*(?:°|掳|deg|DEG)?\s+(?:to|TO)\s+(?P<fix>[A-Z0-9]{2,6})",
    re.IGNORECASE,
)
DIRECT_FIX_RE = re.compile(r"\bdirect\s+(?:to\s+)?(?P<fix>[A-Z0-9]{2,6})\b", re.IGNORECASE)
HOLD_WORD_RE = re.compile(r"\bhold(?:ing)?\b", re.IGNORECASE)
HOLD_AT_FIX_RE = re.compile(r"\bhold(?:ing)?\s+(?:at|on)\s+(?P<fix>[A-Z][A-Z0-9]{2,5})\b", re.IGNORECASE)
HOLDING_PATTERN_AFTER_RE = re.compile(
    r"\b(?:one\s+)?minute\s+holding\s+pattern\s+(?P<fix>[A-Z][A-Z0-9]{2,5})\b",
    re.IGNORECASE,
)
TO_FIX_AND_HOLD_RE = re.compile(
    r"\b(?:to|direct)\s+(?P<fix>[A-Z][A-Z0-9]{2,5})"
    rf"(?:\s+{FACILITY_DESCRIPTOR_RE})?"
    r"(?:\s+INT)?"
    r"(?:/[A-Z0-9.\-\s]+?)?"
    r"(?:\s+\d+(?:\.\d+)?\s*DME)?\s+and\s+hold\b",
    re.IGNORECASE,
)
NAVAID_RADIAL_TO_FIX_RE = re.compile(
    rf"\b(?P<navaid>[A-Z]{{2,5}})\s*(?:{FACILITY_DESCRIPTOR_RE})?\s*"
    r"R[-\s]*[O0]?(?P<radial>\d{2,3})\s+(?:to|TO)\s+(?P<fix>[A-Z][A-Z0-9]{2,5})",
    re.IGNORECASE,
)
IMMEDIATE_FIX_BEFORE_HOLD_RE = re.compile(
    rf"\b(?P<fix>[A-Z][A-Z0-9]{{2,5}})"
    rf"(?:/[A-Z0-9. ]+?)?"
    rf"(?:\s+{FACILITY_DESCRIPTOR_RE})?"
    rf"\s+(?:and\s+)?$",
    re.IGNORECASE,
)


def valid_fix(fix: str, *, allow_runway: bool = True) -> bool:
    fix = fix.upper()
    if fix in BAD_FIX_TOKENS:
        return False
    if any(ch.isdigit() for ch in fix):
        return False
    if not allow_runway and RUNWAY_FIX_RE.match(fix):
        return False
    return True


def suspicious_fix(fix: str) -> bool:
    fix = fix.upper()
    return any(ch.isdigit() for ch in fix) or bool(RUNWAY_FIX_RE.match(fix))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def candidate_to_evidence(group: str, index: int, candidate: dict[str, Any], relation: str, field_type: str | None = None, value: Any | None = None) -> dict[str, Any]:
    return {
        "field_type": field_type or candidate.get("field_type", "other_ocr_candidate"),
        "value": candidate.get("value") if value is None else value,
        "relation_to_leg": relation,
        "source_candidate_group": group,
        "source_candidate_index": index,
        "source_snippet": candidate.get("source_snippet", ""),
        "source_section": candidate.get("source_section", "unknown"),
        "source_start_char": candidate.get("source_start_char"),
        "source_end_char": candidate.get("source_end_char"),
        "rule_id": candidate.get("rule_id", "unknown_rule"),
        "confidence": candidate.get("confidence"),
        "notes": candidate.get("notes"),
    }


def make_leg(index: int, link_type: str, evidence: list[dict[str, Any]], confidence: float | None, notes: str) -> dict[str, Any]:
    starts = [item["source_start_char"] for item in evidence if isinstance(item.get("source_start_char"), int)]
    ends = [item["source_end_char"] for item in evidence if isinstance(item.get("source_end_char"), int)]
    return {
        "candidate_leg_index": index,
        "link_type": link_type,
        "evidence": evidence,
        "source_span_start": min(starts) if starts else None,
        "source_span_end": max(ends) if ends else None,
        "confidence": confidence,
        "notes": notes,
    }


def parse_hold_fix(text: str) -> str | None:
    match = HOLDING_PATTERN_AFTER_RE.search(text)
    if match:
        fix = match.group("fix").upper()
        if valid_fix(fix):
            return fix

    match = TO_FIX_AND_HOLD_RE.search(text)
    if match:
        fix = match.group("fix").upper()
        if valid_fix(fix):
            return fix

    match = HOLD_AT_FIX_RE.search(text)
    if match:
        fix = match.group("fix").upper()
        if valid_fix(fix):
            return fix
    for hold_match in HOLD_WORD_RE.finditer(text):
        prefix = text[: hold_match.start()]
        window = prefix[-120:]
        match = IMMEDIATE_FIX_BEFORE_HOLD_RE.search(window)
        if not match:
            continue
        fix = match.group("fix").upper()
        if valid_fix(fix):
            return fix
    return None


def parse_direct_fix(text: str) -> str | None:
    match = DIRECT_FIX_RE.search(text)
    if not match:
        return None
    fix = match.group("fix").upper()
    if not valid_fix(fix):
        return None
    return fix


def parse_to_fix_and_hold(text: str) -> str | None:
    match = TO_FIX_AND_HOLD_RE.search(text)
    if not match:
        return None
    fix = match.group("fix").upper()
    if not valid_fix(fix):
        return None
    return fix


def parse_navaid_radial_to_fix(text: str) -> tuple[str, int, str] | None:
    match = NAVAID_RADIAL_TO_FIX_RE.search(text)
    if not match:
        return None
    navaid = match.group("navaid").upper()
    radial = int(match.group("radial"))
    fix = match.group("fix").upper()
    if not valid_fix(navaid) or not valid_fix(fix):
        return None
    return navaid, radial, fix


def leg_signature(leg: dict[str, Any]) -> tuple[Any, ...]:
    fixes = tuple(
        str(item.get("value")).upper()
        for item in leg["evidence"]
        if item.get("relation_to_leg") == "fix" and item.get("value") is not None
    )
    courses = tuple(
        str(item.get("value"))
        for item in leg["evidence"]
        if item.get("relation_to_leg") == "course_or_radial" and item.get("value") is not None
    )
    return (leg["link_type"], fixes, courses)


def dedupe_and_reindex_legs(legs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    duplicate_count = 0
    for leg in legs:
        signature = leg_signature(leg)
        if signature in seen:
            duplicate_count += 1
            continue
        seen.add(signature)
        leg = dict(leg)
        leg["candidate_leg_index"] = len(unique)
        unique.append(leg)
    return unique, duplicate_count


def leg_fix_values(leg: dict[str, Any]) -> set[str]:
    return {
        str(item.get("value")).upper()
        for item in leg.get("evidence", [])
        if item.get("relation_to_leg") == "fix" and item.get("value") is not None
    }


def candidate_leg_pair_warnings(legs: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for i, left in enumerate(legs):
        left_fixes = leg_fix_values(left)
        if not left_fixes:
            continue
        for right in legs[i + 1 :]:
            right_fixes = leg_fix_values(right)
            shared = sorted(left_fixes & right_fixes)
            if not shared:
                continue
            if left["link_type"] == "direct_to_fix" and right["link_type"] == "hold_at_fix":
                warnings.append(
                    "direct_to_fix and hold_at_fix share fix "
                    + ",".join(shared)
                    + "; do not collapse a direct-to-fix step and a hold step into one canonical leg without OCR justification"
                )
            if left["link_type"] == "track_to_fix" and right["link_type"] == "hold_at_fix":
                warnings.append(
                    "track_to_fix and hold_at_fix share fix "
                    + ",".join(shared)
                    + "; do not mechanically output both as two canonical legs or merge them without checking OCR prose"
                )
    return warnings


def candidate_leg_suspicious_fix_warnings(legs: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for leg in legs:
        suspicious = sorted(fix for fix in leg_fix_values(leg) if suspicious_fix(fix))
        if not suspicious:
            continue
        warnings.append(
            "candidate_leg "
            + str(leg.get("candidate_leg_index"))
            + " contains suspicious fix token "
            + ",".join(suspicious)
            + "; treat as weak OCR evidence unless missed approach instruction text independently supports it"
        )
    return warnings


def iter_candidates(field_candidates: dict[str, Any], group: str) -> list[tuple[int, dict[str, Any]]]:
    values = field_candidates.get("field_candidates", {}).get(group, [])
    return [(idx, item) for idx, item in enumerate(values) if isinstance(item, dict)]


def build_links(field_candidates: dict[str, Any], source_path: Path) -> dict[str, Any]:
    chart_id = field_candidates["chart_id"]
    candidate_legs: list[dict[str, Any]] = []
    unlinked: list[dict[str, Any]] = []
    warnings: list[str] = []

    leg_index = 0

    for idx, candidate in iter_candidates(field_candidates, "direct_phrase_snippets"):
        text = str(candidate.get("value") or candidate.get("source_snippet") or "")
        fix = parse_direct_fix(text)
        if not fix:
            unlinked.append(unlinked_candidate("direct_phrase_snippets", idx, candidate, "direct phrase did not expose a parseable fix"))
            continue
        evidence = [
            candidate_to_evidence("direct_phrase_snippets", idx, candidate, "phrase"),
            candidate_to_evidence("direct_phrase_snippets", idx, candidate, "fix", "fix_ident", fix),
        ]
        candidate_legs.append(make_leg(leg_index, "direct_to_fix", evidence, 0.66, "direct-to-fix link parsed from OCR phrase only"))
        leg_index += 1

    for idx, candidate in iter_candidates(field_candidates, "track_to_fix_snippets"):
        text = str(candidate.get("value") or candidate.get("source_snippet") or "")
        match = COURSE_TO_FIX_RE.search(text)
        if not match:
            unlinked.append(unlinked_candidate("track_to_fix_snippets", idx, candidate, "track/course phrase did not expose both course and fix"))
            continue
        course = int(match.group("course"))
        fix = match.group("fix").upper()
        if not valid_fix(fix):
            unlinked.append(unlinked_candidate("track_to_fix_snippets", idx, candidate, "track/course phrase exposed a non-fix token"))
            continue
        link_type = "track_to_fix"
        evidence = [
            candidate_to_evidence("track_to_fix_snippets", idx, candidate, "phrase"),
            candidate_to_evidence("track_to_fix_snippets", idx, candidate, "course_or_radial", "course_deg", course),
            candidate_to_evidence("track_to_fix_snippets", idx, candidate, "fix", "fix_ident", fix),
        ]
        candidate_legs.append(make_leg(leg_index, link_type, evidence, 0.72, "course/track-to-fix link parsed from OCR phrase only"))
        leg_index += 1

    for idx, candidate in iter_candidates(field_candidates, "instruction_snippets"):
        text = str(candidate.get("value") or candidate.get("source_snippet") or "")

        radial_link = parse_navaid_radial_to_fix(text)
        if radial_link is not None:
            navaid, radial, fix = radial_link
            evidence = [
                candidate_to_evidence("instruction_snippets", idx, candidate, "phrase"),
                candidate_to_evidence("instruction_snippets", idx, candidate, "context", "other_ocr_candidate", navaid),
                candidate_to_evidence("instruction_snippets", idx, candidate, "course_or_radial", "radial_deg", radial),
                candidate_to_evidence("instruction_snippets", idx, candidate, "fix", "fix_ident", fix),
            ]
            candidate_legs.append(
                make_leg(
                    leg_index,
                    "radial_to_fix",
                    evidence,
                    0.69,
                    "navaid radial-to-fix link parsed from missed approach instruction OCR only",
                )
            )
            leg_index += 1

        hold_fix = parse_to_fix_and_hold(text)
        if hold_fix is not None:
            evidence = [
                candidate_to_evidence("instruction_snippets", idx, candidate, "phrase"),
                candidate_to_evidence("instruction_snippets", idx, candidate, "fix", "fix_ident", hold_fix),
            ]
            candidate_legs.append(
                make_leg(
                    leg_index,
                    "hold_at_fix",
                    evidence,
                    0.67,
                    "hold-to-fix link parsed from missed approach instruction OCR only",
                )
            )
            leg_index += 1

    for idx, candidate in iter_candidates(field_candidates, "hold_candidates"):
        text = str(candidate.get("value") or candidate.get("source_snippet") or "")
        fix = parse_hold_fix(text)
        if not fix:
            unlinked.append(unlinked_candidate("hold_candidates", idx, candidate, "hold phrase did not expose a parseable nearby fix"))
            continue
        evidence = [
            candidate_to_evidence("hold_candidates", idx, candidate, "hold"),
            candidate_to_evidence("hold_candidates", idx, candidate, "fix", "fix_ident", fix),
        ]
        candidate_legs.append(make_leg(leg_index, "hold_at_fix", evidence, 0.58, "hold-to-fix link parsed from OCR phrase only; low-confidence candidate"))
        leg_index += 1

    for group in ("route_sequence_snippets", "instruction_snippets"):
        for idx, candidate in iter_candidates(field_candidates, group):
            unlinked.append(unlinked_candidate(group, idx, candidate, "kept as context only; v0 linker does not convert raw sequence snippets into ordered legs"))

    if not candidate_legs:
        warnings.append("no candidate_legs emitted by v0 linker")
    if any(item.get("source_candidate_group") == "route_sequence_snippets" for item in unlinked):
        warnings.append("route_sequence_snippets are not leg-bound in v0; route-table-heavy procedures may remain unresolved")
    candidate_legs, duplicate_count = dedupe_and_reindex_legs(candidate_legs)
    if duplicate_count:
        warnings.append(f"deduplicated {duplicate_count} repeated candidate_leg entries")
    warnings.extend(candidate_leg_pair_warnings(candidate_legs))

    return {
        "schema_version": SCHEMA_VERSION,
        "chart_id": chart_id,
        "link_source": LINK_SOURCE,
        "source_contract": {
            "source": "same_chart_full_chart_ocr_text_and_flat_field_candidates",
            "uses_flat_field_candidates": True,
            "allows_ocr_bbox": False,
            "allows_chart_image_pixels": False,
            "allows_roi_or_visual_cells": False,
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
        "source_field_candidates": {
            "path": str(source_path),
            "sha256": sha256_file(source_path),
            "schema_version": field_candidates.get("schema_version", ""),
        },
        "candidate_legs": candidate_legs,
        "unlinked_candidates": unlinked,
        "linking_warnings": warnings,
    }


def unlinked_candidate(group: str, index: int, candidate: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "source_candidate_group": group,
        "source_candidate_index": index,
        "field_type": str(candidate.get("field_type", "unknown")),
        "value": candidate.get("value"),
        "reason": reason,
        "source_snippet": candidate.get("source_snippet", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build B1_prime_link field-to-leg candidate links without model calls.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--field-candidates-dir", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    schema = load_json(args.schema)
    samples = read_jsonl(args.manifest)
    results: list[dict[str, Any]] = []

    for sample in samples:
        chart_id = sample["chart_id"]
        source_path = args.field_candidates_dir / f"{chart_id}.json"
        field_candidates = load_json(source_path)
        linked = build_links(field_candidates, source_path)
        jsonschema.validate(linked, schema)
        out_path = args.output_dir / f"{chart_id}.json"
        write_json(out_path, linked)
        results.append(
            {
                "chart_id": chart_id,
                "candidate_legs": len(linked["candidate_legs"]),
                "unlinked_candidates": len(linked["unlinked_candidates"]),
                "warnings": linked["linking_warnings"],
                "output_path": str(out_path),
            }
        )

    write_json(
        args.output_dir / "linking_only_summary.json",
        {
            "schema_version": SCHEMA_VERSION,
            "link_source": LINK_SOURCE,
            "samples_total": len(results),
            "schema_valid": len(results),
            "results": results,
        },
    )
    print(json.dumps({"samples_total": len(results), "schema_valid": len(results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
