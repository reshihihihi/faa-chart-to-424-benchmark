# 外部数据集发布策略 20260504

本仓库只保留代码、schema、prompt、runner、scorer、构造脚本和必要的实验说明。
正式数据集、SFT 训练包、评测输入包、逐样本 manifest payload、PDF/PNG、raw
CIFP、canonical target、人工标注和校验报告应放在外部数据发布包中，不再作为
Git 代码仓库内容提交。

## 当前外部发布包

本机草稿包：

```text
C:/Users/admin/Documents/Code/NIPS-AIP/NIPS-AIP-Dataset-v1.0-draft/
```

该包包含：

- `formal300`：300 张正式样本，paper split 为 50/50/200。
- `auxiliary_sft_train500_dev100`：D-SFT/LoRA 专用 500 train + 100 dev。
- `formal300/annotations/final_by_chart`：300 份最终人工视觉标注。
- `metadata/validation_report.json`：路径、hash、schema、SFT JSONL 校验。
- `metadata/duplicate_near_duplicate_no_overlap_report.json`：formal300 与
  auxiliary SFT 的重复/近重复/no-overlap 检查。
- `DATASET_CARD.md`、`CITATION.cff`、`croissant.json`、`LICENSE`。

## Git 中保留什么

- 数据构造脚本和训练/推理脚本。
- schema、prompt、method registry、no-leakage policy。
- 小体积的说明文档和实验协议。

## Git 中不保留什么

- PNG/PDF 图像数据。
- raw CIFP/424 和 canonical target 答案文件。
- 训练 JSONL、评测输入 JSONL、逐样本 scoring manifest。
- 人工标注 JSON、server submission provenance、validation report。
- LoRA checkpoint、raw outputs、HTML/PNG review、日志和本机路径配置。

如果需要复现实验，先取得外部数据包，再按脚本或 manifest 中的相对路径挂载到
本机运行目录。

