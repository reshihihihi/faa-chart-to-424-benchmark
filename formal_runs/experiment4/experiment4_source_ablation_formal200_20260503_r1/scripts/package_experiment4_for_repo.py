from __future__ import annotations

import json
import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


SOURCE_ROOT = Path(r"formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1")
REPO_ROOT = Path(r".")
RUN_REL = Path("formal_runs/experiment4/experiment4_source_ablation_formal200_20260503_r1")
FREEZE_REL = Path("reports/freeze/experiment4_source_ablation_20260503_r1")
RUN_ROOT = REPO_ROOT / RUN_REL
FREEZE_ROOT = REPO_ROOT / FREEZE_REL

TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".csv", ".py", ".ps1", ".txt"}

REQUIRED_RELS = [
    "reports/experiment4_final_execution_report_zh.md",
    "reports/experiment4_result_analysis_zh.md",
    "reports/experiment4_final_metrics_table.csv",
    "reports/experiment4_final_metrics_summary.json",
    "reports/experiment4_v2_scoring_summary.csv",
    "reports/experiment4_v2_scoring_summary.json",
    "reports/experiment4_freeze_manifest.json",
    "reports/experiment4_analysis_artifacts_manifest.json",
    "reports/experiment4_d1_v2_accuracy_by_variant.png",
    "reports/experiment4_method_v2_accuracy_by_variant.png",
    "reports/experiment4_dsft_raw_vs_d1_coverage_failure.png",
    "reports/experiment4_submission_file_list.json",
    "reports/experiment4_submission_package_manifest_zh.md",
    "baseline/V0_group1_frozen_baseline_manifest.json",
    "manifests/experiment4_evaluation200_chart_ids.json",
    "manifests/experiment4_evaluation200_source_view_manifest.jsonl",
    "manifests/experiment4_manifest_preparation_summary.json",
    "manifests/experiment4_scoring_manifest_eval200.jsonl",
    "source_views/manifests/source_view_manifest.jsonl",
    "validation/input_manifest_no_leakage_final_report.json",
    "validation/source_view_validation_after_residual_guard_report.json",
    "validation/masked_text_residual_ocr_report_final.json",
    "scripts/build_source_views.py",
    "scripts/prepare_experiment4_manifests.py",
    "scripts/run_d1_output_canonicalizer.py",
    "scripts/score_d1_strict.py",
    "scripts/rescore_experiment4_v2.py",
    "scripts/summarize_experiment4_results.py",
    "scripts/create_experiment4_freeze_manifest.py",
    "scripts/generate_experiment4_analysis_artifacts.py",
    "scripts/package_experiment4_for_repo.py",
]

D1_VARIANTS = [
    "V1_ma_text_only",
    "V2_full_minus_ma_prose",
    "V3_plan_view_only",
    "V4_icon_detail_only",
    "V5_plan_detail_no_ma",
]

D1_SUBDIRS = [
    "raw_text",
    "canonical_json",
    "validation",
    "scores",
    "strict_scores",
    "reports",
]


def is_same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except FileNotFoundError:
        return False


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def portable_path(path: Path) -> str:
    try:
        return repo_rel(path)
    except ValueError:
        return sanitize_text(str(path))


def sanitize_text(text: str) -> str:
    out = text
    repo_abs = Path.cwd().resolve()
    run_abs = (repo_abs / RUN_REL).resolve()
    source_abs = (repo_abs / SOURCE_ROOT).resolve() if not SOURCE_ROOT.is_absolute() else SOURCE_ROOT.resolve()
    replacements = [
        (str(run_abs), RUN_REL.as_posix()),
        (str(run_abs).replace("\\", "/"), RUN_REL.as_posix()),
        (str(run_abs).replace("\\", "\\\\"), RUN_REL.as_posix()),
        (str(source_abs), RUN_REL.as_posix()),
        (str(source_abs).replace("\\", "/"), RUN_REL.as_posix()),
        (str(source_abs).replace("\\", "\\\\"), RUN_REL.as_posix()),
        (str(repo_abs), "."),
        (str(repo_abs).replace("\\", "/"), "."),
        (str(repo_abs).replace("\\", "\\\\"), "."),
    ]
    for old, new in replacements:
        out = out.replace(old, new)
    out = re.sub(
        r"[A-Za-z]:[\\/]+experiment3[\\/]+zu4",
        RUN_REL.as_posix(),
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"[A-Za-z]:[\\/]+experiment3[\\/]+github_work[\\/]+faa-chart-to-424-benchmark(?:-[^\\/\"']+)?",
        ".",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"[A-Za-z]:[\\/]+experiment3[\\/]+",
        "external/experiment3/",
        out,
        flags=re.IGNORECASE,
    )
    return out


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in TEXT_SUFFIXES:
        text = src.read_text(encoding="utf-8", errors="replace")
        sanitized = sanitize_text(text)
        if is_same_path(src, dst) and sanitized == text:
            return
        dst.write_text(sanitized, encoding="utf-8", newline="\n")
    else:
        if is_same_path(src, dst):
            return
        shutil.copy2(src, dst)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "relative_path": repo_rel(path),
        "size_bytes": stat.st_size,
        "sha256": sha256(path),
    }


def copy_required_files() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for rel in REQUIRED_RELS:
        src = SOURCE_ROOT / rel
        dst = RUN_ROOT / rel
        if not src.exists():
            records.append({"relative_path": rel, "copied": False, "reason": "missing source"})
            continue
        copy_file(src, dst)
        records.append(
            {
                "relative_path": rel,
                "copied": True,
                "source_size_bytes": src.stat().st_size,
                "destination": repo_rel(dst),
            }
        )
    return records


def copy_d1_outputs() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for variant in D1_VARIANTS:
        local_style_src = SOURCE_ROOT / "runs" / "formal_eval200" / variant / "D1"
        repo_style_src = SOURCE_ROOT / "D1" / variant
        src_root = local_style_src if local_style_src.exists() else repo_style_src
        dst_root = RUN_ROOT / "D1" / variant
        for subdir in D1_SUBDIRS:
            src_dir = src_root / subdir
            dst_dir = dst_root / subdir
            count = 0
            if src_dir.exists():
                for src in sorted(path for path in src_dir.rglob("*") if path.is_file()):
                    rel = src.relative_to(src_dir)
                    copy_file(src, dst_dir / rel)
                    count += 1
            records.append(
                    {
                        "variant": variant,
                        "subdir": subdir,
                        "source": portable_path(src_dir),
                        "destination": repo_rel(dst_dir),
                        "file_count": count,
                    }
            )

        for filename in ["method_summary.json", "summary_report.json"]:
            src = src_root / filename
            dst = dst_root / filename
            if src.exists():
                copy_file(src, dst)
                records.append(
                    {
                        "variant": variant,
                        "file": filename,
                        "destination": repo_rel(dst),
                        "file_count": 1,
                    }
                )
    return records


def write_freeze_readme() -> None:
    FREEZE_ROOT.mkdir(parents=True, exist_ok=True)
    analysis_src = RUN_ROOT / "reports" / "experiment4_result_analysis_zh.md"
    metrics_src = RUN_ROOT / "reports" / "experiment4_final_metrics_table.csv"
    freeze_src = RUN_ROOT / "reports" / "experiment4_freeze_manifest.json"
    for src in [
        analysis_src,
        metrics_src,
        RUN_ROOT / "reports" / "experiment4_d1_v2_accuracy_by_variant.png",
        RUN_ROOT / "reports" / "experiment4_method_v2_accuracy_by_variant.png",
        RUN_ROOT / "reports" / "experiment4_dsft_raw_vs_d1_coverage_failure.png",
    ]:
        copy_file(src, FREEZE_ROOT / src.name)

    readme = f"""# 实验组4 source-view ablation 最终结果包

本目录是实验组4结果在仓库中的 freeze 摘要。完整可复现产物位于：

- `{RUN_REL.as_posix()}`

## 主分析口径

- 主结果：`D1 + chart_display_aware_v2`
- 补充结果：`D_SFT raw` 用于说明 coverage/failure_rate 和输出格式稳定性
- ROI 来源：`prelabel_not_gold`，已人工确认，但不能写成 gold
- PR25 关系：沿用 Group 1 scoring-equivalence v2 和 D1 fixed-output-interface 口径

## 关键结论

1. D_SFT/D1 并不是只靠 missed approach 文本框；遮挡 MA prose 后的 `V2_full_minus_ma_prose` 仍保持较高 D1 v2 accuracy。
2. `plan view` 是最关键的信息来源；`detail/icon` 有补充价值，但单独不足。
3. C4 在 `V1_ma_text_only` 上更好，说明 OCR/规则方法更直接依赖 MA prose。
4. `V1_ma_text_only` 的 D1 低分不代表文字框无信息，而是 D_SFT 在只给局部文本框时输出结构失稳；D1 只修格式，不补答案。

## 文件

- `{repo_rel(analysis_src)}`
- `{repo_rel(metrics_src)}`
- `{repo_rel(freeze_src)}`
- `{repo_rel(RUN_ROOT / 'reports' / 'experiment4_submission_package_manifest_zh.md')}`
"""
    (FREEZE_ROOT / "README_zh.md").write_text(readme, encoding="utf-8", newline="\n")


def write_repo_freeze_manifest() -> Path:
    files = []
    for root in [RUN_ROOT, FREEZE_ROOT]:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.name == "experiment4_freeze_manifest.json":
                continue
            files.append(file_record(path))

    d1_inventory = []
    for variant in D1_VARIANTS:
        variant_root = RUN_ROOT / "D1" / variant
        subdirs = {}
        for subdir in D1_SUBDIRS:
            directory = variant_root / subdir
            paths = sorted(item for item in directory.rglob("*") if item.is_file()) if directory.exists() else []
            digest = hashlib.sha256()
            for path in paths:
                digest.update(path.name.encode("utf-8"))
                digest.update(b"\0")
                digest.update(sha256(path).encode("ascii"))
                digest.update(b"\n")
            subdirs[subdir] = {
                "relative_path": repo_rel(directory),
                "exists": directory.exists(),
                "file_count": len(paths),
                "directory_digest_sha256": digest.hexdigest() if paths else None,
            }
        d1_inventory.append(
            {
                "variant": variant,
                "d1_root": repo_rel(variant_root),
                "subdirs": subdirs,
            }
        )

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Repo-packaged Experiment 4 freeze manifest after local absolute path sanitization.",
        "repo_run_root": RUN_REL.as_posix(),
        "repo_freeze_root": FREEZE_REL.as_posix(),
        "roi_source": "prelabel_not_gold",
        "files": files,
        "d1_output_inventory": d1_inventory,
        "file_count": len(files),
    }
    out = RUN_ROOT / "reports" / "experiment4_freeze_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(out, FREEZE_ROOT / out.name)
    return out


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    file_records = copy_required_files()
    d1_records = copy_d1_outputs()
    write_freeze_readme()
    repo_freeze_manifest = write_repo_freeze_manifest()

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": "local experiment4 workspace",
        "repo_run_root": RUN_REL.as_posix(),
        "repo_freeze_root": FREEZE_REL.as_posix(),
        "required_files": file_records,
        "d1_outputs": d1_records,
        "repo_freeze_manifest": repo_rel(repo_freeze_manifest),
        "note": "Text artifacts were sanitized to remove local absolute paths before packaging.",
    }
    out = RUN_ROOT / "experiment4_repo_package_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Packaged run root: {RUN_ROOT}")
    print(f"Packaged freeze root: {FREEZE_ROOT}")
    missing = [record for record in file_records if not record.get("copied")]
    if missing:
        print(f"Missing required sources: {len(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
