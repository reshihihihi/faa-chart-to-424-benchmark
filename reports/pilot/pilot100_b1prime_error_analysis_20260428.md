# Pilot100 B1_prime Error Analysis, 2026-04-28

## Scope

本报告只分析 `<external-artifact-root>/try_B1_B1_prime\predictions\pilot100_b1_b1prime_gpt54_toolcall_schema_retry1_ordinary_ocr_20260428_r1` 中已经完成的 100 张 external pilot 结果。

分析目标是解释为什么 B1_prime 在 100 张上低于 B1，并决定当前 B1_prime matcher 是否可以冻结。这里使用 score/target 只做事后误差分析，不进入 B1_prime 输入、prompt、matcher 或 rerun 逻辑。

## Method Boundary Being Checked

| Method | Input boundary | Model | Output control |
|---|---|---|---|
| B1 | OCR-1 full-chart text only | gpt-5.4 | forced `emit_canonical_json` tool call |
| B1_prime | OCR-1 full-chart text + OCR-text-only flat `field_candidates` | gpt-5.4 | forced `emit_canonical_json` tool call |

B1_prime 的 `field_candidates` 是扁平候选，不含 `leg_index`、不含 field-to-leg linking、不含 target/scorer/CIFP/ARINC 424。

## Overall Result

| Method | Schema-valid | Correct / Total | Accuracy | Schema retries |
|---|---:|---:|---:|---:|
| B1 | 100/100 | 723 / 2344 | 0.3084 | 7 |
| B1_prime | 100/100 | 674 / 2344 | 0.2875 | 11 |

B1_prime 比 B1 低 49 个字段，约低 2.09 个百分点。

## Main Finding

B1_prime 低于 B1 的主要原因不是普遍小幅变差，而是 7 张图输出了 schema-valid 的空 missed approach：

```json
{"leg_count":{"status":"unknown","value":null},"legs":[]}
```

这 7 张是：

| Chart | Type | Target legs | B1 | B1_prime | Delta |
|---|---|---:|---:|---:|---:|
| KAAF_R32 | RNAV_RWY | 3 | 4/19 | 0/19 | -4 |
| KAWO_L34 | LOC | 3 | 6/19 | 0/19 | -6 |
| KBDE_R30 | RNAV_RWY | 5 | 9/31 | 0/31 | -9 |
| KBOS_I04R | ILS_OR_LOC | 2 | 5/13 | 0/13 | -5 |
| KDWH_L17R | LOC | 4 | 9/25 | 0/25 | -9 |
| KHRF_RNV-A | RNAV_CIRCLING | 6 | 5/37 | 0/37 | -5 |
| KOLY_R11 | RNAV_RWY | 2 | 7/13 | 0/13 | -7 |

这 7 张贡献了 -45 个字段差异。其余 93 张合计只差 -4 个字段。因此当前 B1_prime 的问题集中在“候选输入使模型放弃构建 legs”的失败模式，而不是 B1_prime 在所有样本上稳定弱于 B1。

这 7 张都是第一次 tool call 就 schema-valid，没有触发 schema retry；所以这不是 JSON 格式或 schema 验证失败，而是方法语义输出失败。

## Field-Level Differences

| Field | B1 | B1_prime | Delta | B1-only correct | B1_prime-only correct |
|---|---:|---:|---:|---:|---:|
| leg_count | 30/100 | 23/100 | -7 | 8 | 1 |
| Q_terminator | 59/374 | 102/374 | +43 | 22 | 65 |
| Q1_fix_ident | 167/374 | 139/374 | -28 | 65 | 37 |
| Q2_altitude_constraint | 9/374 | 16/374 | +7 | 7 | 14 |
| Q3_turn | 212/374 | 186/374 | -26 | 57 | 31 |
| Q4_course_or_radial | 58/374 | 51/374 | -7 | 22 | 15 |
| Q5_hold_params | 188/374 | 157/374 | -31 | 36 | 5 |

B1_prime 确实提高了 `Q_terminator` 和少量 altitude 字段，说明 flat candidates 对 path terminator/altitude 线索可能有帮助。但它同时伤害了 leg_count、fix、turn、hold，尤其是 129 个 leg-field 位置因为 predicted legs 缺失而成为 `pred=null`。

## Procedure-Type Pattern

| Procedure type | N | B1 | B1_prime | Delta |
|---|---:|---:|---:|---:|
| ILS_OR_LOC | 29 | 238/635 = 0.375 | 189/635 = 0.298 | -49 |
| LOC | 20 | 149/386 = 0.386 | 127/386 = 0.329 | -22 |
| RNAV_CIRCLING | 18 | 95/468 = 0.203 | 107/468 = 0.229 | +12 |
| RNAV_RWY | 30 | 211/798 = 0.264 | 222/798 = 0.278 | +11 |
| VOR | 3 | 30/57 = 0.526 | 29/57 = 0.509 | -1 |

B1_prime 在 RNAV 类略好，但在 ILS/LOC/LOC 明显更差。这个模式符合候选层对 localizer、facility、briefing/procedure notes、missed approach fix 图注等文本更容易产生噪声的判断。

## Candidate-Layer Evidence

100 张的 `field_candidates` 总体规模：

| Candidate type | Count |
|---|---:|
| fix_ident | 3642 |
| altitude_ft | 2382 |
| hold_phrase | 202 |
| radial_deg | 179 |
| runway_ident | 173 |
| climb_phrase | 127 |
| course_deg | 96 |
| direct_phrase | 73 |
| turn_direction | 67 |
| heading_deg | 22 |

每张图平均约 69.6 个 candidates，中位数 71，范围 36 到 83。`fix_candidates` 经常达到上限 40。

高频 `fix/runway` 候选中包含大量不是真实 fix ident 的词或图面标签，例如：

| Value | Count | Problem |
|---|---:|---|
| CHAN | 102 | channel label |
| LOC | 101 | facility/procedure type, not fix ident |
| CON | 97 | comm label fragment |
| IAF | 87 | procedure role label |
| FOR | 85 | ordinary word |
| NOT | 78 | ordinary word |
| LDG | 66 | runway landing label |
| TRACK | 63 | procedure word |
| WHEN | 58 | ordinary word |
| FEET | 52 | unit word |
| ALL | 52 | ordinary word |
| VGSI | 49 | visual glide slope label |
| VNAV | 47 | procedure/minima label |

这些候选满足“不是 target/scorer 泄漏”的边界，但 precision 太低，会把 B1_prime 的额外输入变成噪声提示。

## Source-Section Problem

当前 matcher 的 `source_section` 也不够可信。它有两类问题：

1. `missed_approach_spans()` 从 `MISSED APPROACH` 后截取固定窗口，容易把 notes、communications、plan view、profile view 文本都标成 `missed_approach_text`。
2. `infer_source_section()` 只要 snippet window 里包含 `MISSED APPROACH`，即使 token 本身在 label 前，也可能被标成 `missed_approach_text`。

典型例子：

- `KBOS_I04R` 的 OCR 文本中，`MISSED APPROACH:` 后先出现 simultaneous approach notes，再出现真正的 `Climb to 3000 on BOS VOR/DME R-030 to WAXEN/BOS 14 DME and hold.`。B1 能从 OCR 文本抽出 2 legs，但 B1_prime 看到大量候选后输出 empty unknown。
- `KAAF_R32` 的 candidates 中混入 `BARO/VNAV/WHEN/USING/LOCAL/NOT/USE/LNAV` 等候选，B1 输出 2 legs，B1_prime 输出 empty unknown。

## Interpretation

当前 B1_prime 的额外候选层没有引入 target/scorer，也没有越过方法边界；问题在于候选质量和提示控制：

1. Flat candidates 的 precision 不够，尤其是 fix candidates。
2. `source_section` 过度标注为 `missed_approach_text`，削弱了候选排序的可信度。
3. B1_prime prompt 中“如果 number/order 不能可靠确定，就输出 unknown + empty legs”的规则本身合理，但在候选噪声很高时会导致模型过度保守。
4. 因为 output 100/100 schema-valid，格式控制已经可用；当前问题不是 parser repair、JSON code fence、schema failure。

## Decision

不建议冻结当前 `ocr_text_only_regex_field_matcher_pilot_v3`。

B1_prime 方法思想可以保留为 candidate：OCR-1 text + OCR-text-only flat field candidates + LLM，不加入 image、bbox、ROI、field-to-leg linking、target、scorer、CIFP/ARINC 424。
但当前 matcher v3 应修改后用新 run_id 重跑 100 张，再决定是否冻结。

## Boundary-Safe Next Changes

允许修改的范围：

- 改进 missed approach prose span 提取，优先只截取真正 procedure instruction，而不是固定 900 字符窗口。
- 扩展 stopword / non-fix label 过滤，例如 `CHAN, LOC, CON, IAF, FAF, VGSI, VNAV, LNAV, FEET, TRACK, WHEN, NOT, USE, USING, LOCAL, INTL, LDG`。
- 降低或分层限制 `fix_candidates` 数量，避免每张图固定接近 40 个 noisy fix。
- 将候选分成 `high_precision_procedure_candidates` 与 `other_chart_candidates`，但仍保持 flat candidates，不提供 leg_index 或 field-to-leg linking。
- 在 prompt 中强调 candidates 是 weak evidence，若 candidates 与 OCR prose 冲突，应以 OCR prose 的 missed approach instruction 为主。

禁止修改的范围：

- 不能使用 canonical target、score rows、CIFP/ARINC 424、human annotation、gold evidence。
- 不能加入 field-to-leg linking、leg_index、candidate_leg_id、schema_field、expected_value。
- 不能为了这 7 张坏例子写 chart-specific 或 target-aware 规则。
- 不能按分数选择性 rerun。

## Recommended Next Action

建立 `field_matcher_v4_candidate`，只做边界内降噪，然后用新 run_id 重跑 B1_prime 的同一 100 张。重跑前记录：

- matcher version/hash
- prompt hash
- field_candidates schema hash
- OCR-1 artifact root/hash manifest
- run_id
- no-target/no-scorer audit

如果 v4 仍显著低于 B1，B1_prime 应作为 diagnostic/candidate 方法暂不纳入正式冻结；如果 v4 修复 empty-output 失败且保持 schema-valid，再进入预冻结审查。
