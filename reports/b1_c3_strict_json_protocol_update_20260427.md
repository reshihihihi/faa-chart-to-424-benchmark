# B1 / C3 strict JSON protocol update - 2026-04-27

## 目的

本次变更只处理 pilot 中发现的统一格式问题：B1 和 C3 的 raw model output 均被模型包在 markdown code fence 中，导致正式实验中不满足“裸 JSON 输出”要求。

本次变更不根据分数调 prompt，不修改 B1 / C3 的方法边界，不引入 target、CIFP、annotation、field matching、ROI 或人工修复信息。

## 变更内容

1. B1 prompt 删除实际 markdown code fence 行，并追加严格原始输出协议。
2. C3 prompt 删除实际 markdown code fence 行，并追加严格原始输出协议。
3. prompt 中不再保留实际的三个反引号序列，避免模型模仿输出 code fence。
4. `scripts/run_b1_c3_pilot10_current.py` 默认改为 strict JSON only。
5. 正式风格运行中，raw response 必须直接通过 `json.loads(raw.strip())`。
6. markdown code fence、前后解释文字、从长文本中截取第一个 JSON 对象，均不再作为默认可接受解析策略。
7. 保留 `--allow-non-strict-json` 作为 pilot-only 兼容开关，但正式风格运行不应使用。

## 当前文件 hash

| 文件 | SHA256 |
|---|---|
| `prompts/paper_v2/b1_ocr_to_canonical_pilot10.zh_v1_candidate.md` | `F2A2C27B534F93BB33D90834CC9FDDE4726E8AE267BB3D1134679827D1E2F2E3` |
| `prompts/paper_v2/c3_questionnaire_pilot10.zh_v1_candidate.md` | `49E2BA9134E9C7737D98374786963424546123129C6FAA7D648DE8224E468E4E` |
| `scripts/run_b1_c3_pilot10_current.py` | `84B9ED0C10E1A78DB63D484F514F4EE6A07DF6C004E28E87C41336F41DE447D7` |

## 校验

- 脚本语法检查：通过。
- B1 prompt 中实际 code fence 序列：无。
- C3 prompt 中实际 code fence 序列：无。

## 下一步建议

使用新的 strict JSON 协议重跑 pilot10：

```text
run_id: pilot10_exp1_b1_c3_strict_json_20260427_r1
```

重跑后重点检查：

1. `strict_json` 是否达到 10/10。
2. `single_fenced_json_block` 是否降为 0/10。
3. B1 / C3 是否仍能 schema-valid。
4. 如果 strict parse 失败，失败应记录为 format violation，而不是自动修复。
