from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION_FIELDS = [
    "Q_terminator",
    "Q1_fix_ident",
    "Q2_altitude_constraint",
    "Q3_turn",
    "Q4_course_or_radial",
    "Q5_hold_params",
]


def questionnaire_to_canonical(questionnaire_obj: dict) -> dict:
    questionnaire = questionnaire_obj["questionnaire"]
    canonical_legs = []
    for leg in questionnaire.get("legs", []):
        canonical_legs.append(
            {
                "leg_index": leg["leg_index"],
                "answers": {field: leg[field] for field in QUESTION_FIELDS},
            }
        )

    return {
        "chart_id": questionnaire_obj["chart_id"],
        "procedure": questionnaire_obj["procedure"],
        "missed_approach": {
            "leg_count": questionnaire["Q0_leg_count"],
            "legs": canonical_legs,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministically convert C3 questionnaire JSON to canonical JSON."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    canonical = questionnaire_to_canonical(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(canonical, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
