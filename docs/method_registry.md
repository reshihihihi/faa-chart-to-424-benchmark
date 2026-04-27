# Method Registry

Status: pilot candidate, not formal frozen.

This registry records method boundaries for the current paper-v2 pilot. Formal
evaluation must not treat these entries as frozen until the freeze checklist and
experiment manifest are updated.

## B1

Method boundary:

```text
full chart image
  -> full-chart OCR text
  -> LLM
  -> canonical JSON
```

Allowed inputs:

- chart metadata needed to identify the sample;
- full-chart OCR text generated for the current run;
- the canonical output schema contract.

Forbidden inputs:

- chart image pixels at the LLM extraction stage;
- OCR bbox or region labels;
- automatic field candidates;
- ROI crops or prelabels;
- gold observable evidence;
- CIFP or ARINC 424 records;
- canonical proxy target or answer key;
- scorer output;
- manual annotation or manual field-to-leg mapping;
- previous outputs for the same chart.

Purpose:

Measure whether a text LLM can recover missed-approach canonical structure from
full-chart OCR text alone.

## C3

Method boundary:

```text
full chart image
  -> VLM fixed questionnaire JSON
  -> deterministic questionnaire-to-canonical parser
  -> canonical JSON
```

Allowed inputs:

- chart metadata needed to identify the sample;
- full chart image;
- the questionnaire output contract.

Forbidden inputs:

- external OCR text;
- OCR bbox or region labels;
- automatic field candidates;
- ROI crops or prelabels;
- gold observable evidence;
- CIFP or ARINC 424 records;
- canonical proxy target or answer key;
- scorer output;
- manual annotation or manual field-to-leg mapping;
- previous outputs for the same chart.

Purpose:

Measure whether a fixed VLM questionnaire reduces output-format failures and
hallucination relative to unconstrained image-to-JSON extraction.

## Pilot-only strict JSON control

The 2026-04-27 pilot found that prompt text alone did not prevent markdown JSON
code fences. The current pilot candidate therefore uses:

```text
assistant prefill: "{"
strict parser: json.loads(raw.strip())
accepted extraction policy: strict_json only
```

This control changes the transport/output protocol only. It does not provide
new task information, target values, field candidates, ROI information, or
domain-rule prompt content.
