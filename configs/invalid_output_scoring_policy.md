# Invalid Output Scoring Policy

Status: frozen for Group 1 formal evaluation.

Last updated: 2026-04-29.

## Principle

Parse failures, schema failures, API failures after the allowed rerun policy, and
missing predictions must remain in the denominator. They must not be dropped
from the formal table.

## Frozen Policy

For any Group 1 method on a formal sample:

```text
invalid_output_policy = zero_for_all_target_fields
```

If a method has no schema-valid canonical JSON prediction after its pre-registered
allowed attempts, the scorer assigns:

```text
correct = 0
total = number of target fields for that sample
accuracy = 0.0
```

The target field count is:

```text
1 leg_count field + 6 questionnaire fields for each target leg
```

This applies to:

- JSON parse failure;
- canonical schema failure;
- semantic validation failure;
- API failure after allowed infrastructure rerun policy is exhausted;
- missing prediction file.

## What Is Not Allowed

The scorer must not:

- drop failed samples;
- remove failed fields from the denominator;
- infer a partial score from raw text when canonical JSON is invalid;
- repair JSON;
- repair schema fields;
- use model confidence or retry count to adjust score;
- give credit for fields inside a non-schema-valid output.

## Rationale

The paper compares extraction methods. A method that cannot emit a valid output
for a sample has failed all fields that would have been scored on that sample.
Dropping such samples would inflate accuracy and bias comparisons toward methods
with more parse or schema failures.

## Implementation

Implemented by:

```text
scripts/scorers/group1_canonical_field_scorer.py
```

Required CLI mode for invalid predictions:

```text
--invalid-output-policy zero_for_all_target_fields
--failure-type parse_failure|schema_failure|api_failure|missing_prediction
```
