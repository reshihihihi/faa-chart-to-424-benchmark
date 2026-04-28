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
RUN_OUTPUT_ROOT = ROOT / "local_runs"
OCR_SOURCE_ROOT = ROOT / "predictions" / "pilot10_external"
sys.path.insert(0, str(ROOT / "scripts"))

from run_pilot10_anthropic import (
    fill_prompt,
    get_client,
    image_block,
    read_jsonl,
    resolve_package_path,
    save_raw_response,
    score_canonical,
    sha256_file,
    validate_canonical,
    write_json,
    write_text,
)


DEFAULT_RUN_ID = "pilot10_exp1_b1prime_c4_semantic_matcher_v3_next_probe"
DEFAULT_OCR_RUN_ID = "pilot10_exp1_b1_c3_strict_json_prefill_20260427_r1"

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
    "TO",
    "TURN",
    "VOR",
    "VORTAC",
    "WAYPOINT",
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
}

SOURCE_SECTION_RANK = {
    "missed_approach_text": 0,
    "plan_view": 1,
    "profile_view": 1,
    "briefing_strip": 2,
    "full_chart_unknown": 3,
    "unknown": 4,
}


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
    if "MISSED APPROACH" in upper or "MISSED APCH" in upper or "MISSED" in upper:
        return "missed_approach_text"
    if "PROFILE" in upper or "VGSI" in upper:
        return "profile_view"
    if "PLANVIEW" in upper or "PLAN VIEW" in upper:
        return "plan_view"
    if "BRIEFING" in upper:
        return "briefing_strip"
    return "full_chart_unknown"


def missed_approach_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in re.finditer(r"\bMISSED\s+(?:APPROACH|APCH)\b:?", text, flags=re.IGNORECASE):
        start = match.start()
        search_end = min(len(text), start + 900)
        end = search_end
        local = text[start:search_end]
        boundary = re.search(
            r"\n\s*(?:CATEGORY|CIRCLING|Apt Elev|TDZE|TCH|MIRL|REIL|HIRL|NOTE:|Chart|PROFILE)\b",
            local,
            flags=re.IGNORECASE,
        )
        if boundary and boundary.start() > 80:
            end = start + boundary.start()
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


def candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, str]:
    section = candidate.get("source_section") or "unknown"
    start = candidate.get("source_start_char")
    return (
        SOURCE_SECTION_RANK.get(section, 9),
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

    fix_candidates = []
    for match in re.finditer(r"\b[A-Z][A-Z0-9]{2,5}\b", upper):
        token = match.group(0)
        if token in STOPWORDS or token.startswith("RW") or token.startswith("Rwy".upper()) or token.isdigit():
            continue
        fix_candidates.append(
            make_candidate(
                value=token,
                field_type="fix_ident",
                text=ocr_text,
                start=match.start(),
                end=match.end(),
                rule_id="fix_ident_token_regex_v3",
                ma_spans=ma_spans,
            )
        )

    for match in re.finditer(r"\b(?:RWY|RUNWAY)\s*([0-3]?[0-9][LCR]?)\b", upper):
        fix_candidates.append(
            make_candidate(
                value=f"RW{match.group(1)}",
                field_type="runway_ident",
                text=ocr_text,
                start=match.start(),
                end=match.end(),
                rule_id="runway_ident_regex_v3",
                ma_spans=ma_spans,
            )
        )

    altitude_candidates = []
    for match in re.finditer(r"\b([1-9][0-9]{2,4})\b", upper):
        value = int(match.group(1))
        if 300 <= value <= 18000:
            altitude_candidates.append(
                make_candidate(
                    value=value,
                    field_type="altitude_ft",
                    text=ocr_text,
                    start=match.start(),
                    end=match.end(),
                    rule_id="altitude_ft_regex_v3",
                    ma_spans=ma_spans,
                )
            )

    turn_candidates = []
    for match in re.finditer(r"\bLEFT\b|\bLT\b", upper):
        turn_candidates.append(
            make_candidate(
                value="LEFT",
                field_type="turn_direction",
                text=ocr_text,
                start=match.start(),
                end=match.end(),
                rule_id="turn_direction_regex_v3",
                ma_spans=ma_spans,
            )
        )
    for match in re.finditer(r"\bRIGHT\b|\bRT\b", upper):
        turn_candidates.append(
            make_candidate(
                value="RIGHT",
                field_type="turn_direction",
                text=ocr_text,
                start=match.start(),
                end=match.end(),
                rule_id="turn_direction_regex_v3",
                ma_spans=ma_spans,
            )
        )

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
            course_candidates.append(
                make_candidate(
                    value=value,
                    field_type=field_type,
                    text=ocr_text,
                    start=match.start(1),
                    end=match.end(1),
                    rule_id="course_heading_radial_regex_v3",
                    ma_spans=ma_spans,
                )
            )
    for match in re.finditer(r"\b([0-3][0-9]{2})\s*(?:DEG|DEGREES|°)\b", upper):
        value = int(match.group(1))
        if 1 <= value <= 360:
            course_candidates.append(
                make_candidate(
                    value=value,
                    field_type="course_deg",
                    text=ocr_text,
                    start=match.start(1),
                    end=match.end(1),
                    rule_id="degree_value_regex_v3",
                    ma_spans=ma_spans,
                )
            )

    hold_candidates = phrase_candidates(
        ocr_text,
        r"\bHOLD(?:ING)?\b",
        field_type="hold_phrase",
        rule_id="hold_phrase_regex_v3",
        ma_spans=ma_spans,
        window=80,
        limit=20,
    )
    direct_snippets = phrase_candidates(
        ocr_text,
        r"\bDIRECT\b",
        field_type="direct_phrase",
        rule_id="direct_phrase_regex_v3",
        ma_spans=ma_spans,
        window=80,
        limit=20,
    )
    climb_snippets = phrase_candidates(
        ocr_text,
        r"\bCLIMB\b",
        field_type="climb_phrase",
        rule_id="climb_phrase_regex_v3",
        ma_spans=ma_spans,
        window=80,
        limit=20,
    )

    return {
        "schema_version": "field_candidates_schema_v1_candidate",
        "chart_id": chart_id,
        "candidate_source": "ocr_text_only_regex_field_matcher_pilot_v3",
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
                total_limit=40,
                section_limits={
                    "missed_approach_text": 30,
                    "plan_view": 8,
                    "profile_view": 8,
                    "briefing_strip": 4,
                    "full_chart_unknown": 10,
                    "unknown": 4,
                },
            ),
            "altitude_candidates": sorted_unique_candidates_by_section(
                altitude_candidates,
                total_limit=30,
                section_limits={
                    "missed_approach_text": 20,
                    "plan_view": 8,
                    "profile_view": 8,
                    "briefing_strip": 4,
                    "full_chart_unknown": 8,
                    "unknown": 4,
                },
            ),
            "turn_candidates": sorted_unique_candidates(turn_candidates, limit=4),
            "course_candidates": sorted_unique_candidates_by_section(
                course_candidates,
                total_limit=30,
                section_limits={
                    "missed_approach_text": 12,
                    "plan_view": 10,
                    "profile_view": 10,
                    "briefing_strip": 4,
                    "full_chart_unknown": 8,
                    "unknown": 4,
                },
            ),
            "hold_candidates": hold_candidates,
            "direct_phrase_snippets": direct_snippets,
            "climb_phrase_snippets": climb_snippets,
        },
    }


def call_model_json_prefill(
    client: Any,
    *,
    model: str,
    prompt: str,
    image_path: Path | None,
    max_tokens: int,
    temperature: float,
) -> tuple[str, Any]:
    content: list[dict[str, Any]] = []
    if image_path is not None:
        content.append(image_block(image_path))
    content.append({"type": "text", "text": prompt})
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "user", "content": content},
            {"role": "assistant", "content": "{"},
        ],
    )
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return ("{" + "\n".join(text_parts).strip()).strip(), response


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
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens-b1-prime", type=int, default=4096)
    parser.add_argument("--max-tokens-c4", type=int, default=4096)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--ocr-run-id", default=DEFAULT_OCR_RUN_ID)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dir = RUN_OUTPUT_ROOT / args.run_id
    if run_dir.exists() and not args.dry_run:
        raise RuntimeError(f"Run directory already exists: {run_dir}")

    manifest_path = DATA_DIR / "pilot10_manifest.jsonl"
    rows = read_jsonl(manifest_path)[: args.limit]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    ocr_source_dir = OCR_SOURCE_ROOT / args.ocr_run_id / "OCR" / "full_chart_text"

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
        "api": {
            "provider": "anthropic_compatible",
            "base_url_env": "ANTHROPIC_BASE_URL",
            "auth_env": "ANTHROPIC_AUTH_TOKEN",
            "token_value_recorded": False,
        },
        "reused_frozen_or_prefrozen_assets": {
            "schema": {
                "path": str(SCHEMA_PATH.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(SCHEMA_PATH),
                "status": "frozen_canonical_json_contract_v1",
            },
            "parser_policy": {
                "strict_json_only": True,
                "assistant_prefill_json": True,
                "assistant_prefill_value": "{",
                "semantic_repair": False,
                "code_fence_stripping_allowed": False,
            },
            "ocr_artifact_source_for_pilot": str(ocr_source_dir.relative_to(ROOT)).replace("\\", "/"),
        },
        "new_temporary_prefreeze_required": {
            "B1_prime_field_candidates_schema": "field_candidates_schema_v1_candidate",
            "B1_prime_field_matcher_rules": "pilot_candidate_regex_ocr_text_only_v3",
            "C4_allowed_forbidden_inputs": "pilot_candidate",
            "B1_prime_prompt": "candidate_not_frozen",
            "C4_prompt": "candidate_not_frozen",
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

    client = get_client()
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
            error = f"missing_ocr_text:{ocr_text_path}"
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
                model=args.model,
                prompt=prompt,
                image_path=None,
                max_tokens=args.max_tokens_b1_prime,
                temperature=args.temperature,
            )
            write_text(run_dir / "B1_prime" / "raw_text" / f"{chart_id}.txt", text)
            save_raw_response(run_dir / "B1_prime" / "raw_responses" / f"{chart_id}.json", response)
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
                model=args.model,
                prompt=prompt,
                image_path=image_path,
                max_tokens=args.max_tokens_c4,
                temperature=args.temperature,
            )
            write_text(run_dir / "C4" / "raw_text" / f"{chart_id}.txt", text)
            save_raw_response(run_dir / "C4" / "raw_responses" / f"{chart_id}.json", response)
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
