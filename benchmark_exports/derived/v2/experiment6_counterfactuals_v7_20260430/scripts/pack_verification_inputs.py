#!/usr/bin/env python3
"""Pack labeled Experiment 6 cases into label-free verifier inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_ocr_manifest(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if path is None:
        return {}
    return {row["chart_id"]: row for row in read_jsonl(path)}


def pack_case(
    case: Dict[str, Any],
    variant: str,
    repo_root: Path,
    ocr_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    base = {
        "verification_case_id": case["verification_case_id"],
        "chart_id": case["chart_id"],
        "sample_id": case["sample_id"],
        "candidate_record": case["candidate_record"],
    }
    if variant == "v0_candidate_only":
        return base
    if variant == "v1_text_only":
        ocr = ocr_index.get(case["chart_id"])
        if ocr is None:
            raise ValueError(f"missing OCR record for {case['chart_id']}")
        text_rel = ocr["full_text_path"]
        text_abs = repo_root / text_rel
        ocr_text = text_abs.read_text(encoding="utf-8")
        base.update(
            {
                "text_source": "OCR-1 full-chart text",
                "ocr_id": ocr.get("ocr_id"),
                "ocr_engine": ocr.get("engine"),
                "ocr_version": ocr.get("ocr_version"),
                "ocr_text_path": text_rel,
                "ocr_text_sha256": ocr.get("full_text_sha256"),
                "ocr_text_lines": ocr_text.splitlines(),
            }
        )
        return base
    if variant in {"v2_direct_vlm", "v3_direct_vlm"}:
        base["image_path"] = case["image_path"]
        base["image_sha256"] = case["image_sha256"]
        return base
    if variant == "v3_extract_then_compare":
        return base
    raise ValueError(f"unsupported variant: {variant}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument(
        "--variant",
        required=True,
        choices=["v0_candidate_only", "v1_text_only", "v2_direct_vlm", "v3_direct_vlm", "v3_extract_then_compare"],
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ocr-manifest", default="")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    ocr_manifest = Path(args.ocr_manifest) if args.ocr_manifest else None
    ocr_index = read_ocr_manifest(ocr_manifest)

    out = Path(args.out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for case in read_jsonl(Path(args.cases_jsonl)):
            packed = pack_case(case, args.variant, repo_root, ocr_index)
            f.write(json.dumps(packed, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {args.variant} packed inputs to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
