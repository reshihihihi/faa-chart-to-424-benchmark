#!/usr/bin/env python3
"""Compute chart-cluster bootstrap CIs and paired-delta CIs from scored outputs."""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import io
import json
import math
import random
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_OBJECT_CACHE: dict[tuple[str, str], bytes] = {}


@dataclass
class UnitScore:
    numerator: float = 0.0
    denominator: float = 0.0
    rows: int = 0
    filled_missing: bool = False


@dataclass
class MethodScores:
    method: str
    source_files: set[str] = field(default_factory=set)
    units: dict[str, UnitScore] = field(default_factory=dict)
    raw_rows: int = 0


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_text(text: str, source: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid JSON: {exc}") from exc


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            yield obj


def read_jsonl_text(text: str, source: str) -> Iterable[dict[str, Any]]:
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{line_no}: invalid JSONL: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{source}:{line_no}: expected JSON object")
        yield obj


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(ref: str, path: str) -> bytes:
    cached = GIT_OBJECT_CACHE.get((ref, path))
    if cached is not None:
        return cached
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    GIT_OBJECT_CACHE[(ref, path)] = proc.stdout
    return proc.stdout


def git_batch_load(ref: str, paths: list[str]) -> None:
    missing = [path for path in paths if (ref, path) not in GIT_OBJECT_CACHE]
    if not missing:
        return
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    query = "".join(f"{ref}:{path}\n" for path in missing).encode("utf-8")
    stdout, stderr = proc.communicate(query)
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace"))
    offset = 0
    for path in missing:
        line_end = stdout.index(b"\n", offset)
        header = stdout[offset:line_end].decode("utf-8", errors="replace")
        offset = line_end + 1
        if header.endswith(" missing"):
            raise FileNotFoundError(f"{ref}:{path}")
        parts = header.split()
        if len(parts) != 3:
            raise RuntimeError(f"Unexpected git cat-file header for {ref}:{path}: {header!r}")
        size = int(parts[2])
        data = stdout[offset : offset + size]
        offset += size
        if offset < len(stdout) and stdout[offset : offset + 1] == b"\n":
            offset += 1
        GIT_OBJECT_CACHE[(ref, path)] = data


def git_text(ref: str, path: str) -> str:
    return git_bytes(ref, path).decode("utf-8")


def git_ls(ref: str, pattern: str) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return sorted(path for path in proc.stdout.splitlines() if fnmatch.fnmatchcase(path, pattern))


def source_id(ref: str | None, path: Path | str) -> str:
    path_text = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    if ref:
        return f"{ref}:{path_text}"
    return rel(Path(path_text))


def source_sha256(identifier: str) -> str | None:
    if ":" in identifier and not re.match(r"^[A-Za-z]:[\\/]", identifier):
        ref, path = identifier.split(":", 1)
        try:
            return sha256_bytes(git_bytes(ref, path))
        except Exception:
            return None
    path = REPO_ROOT / identifier
    return sha256(path) if path.exists() else None


def get_value(row: dict[str, Any], key: str) -> Any:
    value: Any = row
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise KeyError(key)
    return value


def to_float(value: Any, *, path: Path | str, key: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{path}: key {key!r} is not numeric: {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path}: key {key!r} is not numeric: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{path}: key {key!r} is not finite: {value!r}")
    return number


def metric(numerators: list[float], denominators: list[float], indices: list[int]) -> float | None:
    num = sum(numerators[i] for i in indices)
    den = sum(denominators[i] for i in indices)
    if den <= 0:
        return None
    return num / den


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    weight = pos - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def derive_method(path: Path | str, regex: str, template: str | None = None) -> str:
    if isinstance(path, Path):
        normalized = path.as_posix()
        candidates = [path.name, normalized, str(path)]
    else:
        normalized = str(path).replace("\\", "/")
        candidates = [Path(normalized).name, normalized, str(path)]
    for candidate in candidates:
        match = re.search(regex, candidate)
        if match:
            if template:
                values: dict[str, str] = {}
                values.update({str(index): value for index, value in enumerate(match.groups(), start=1)})
                values.update(match.groupdict())
                return template.format(**values)
            if "method" in match.groupdict():
                return match.group("method")
            return match.group(1)
    raise ValueError(f"Could not derive method name for {path} with regex {regex!r}")


def add_unit_score(method_scores: MethodScores, unit_id: str, numerator: float, denominator: float) -> None:
    if denominator < 0:
        raise ValueError(f"{method_scores.method}/{unit_id}: denominator must be non-negative")
    score = method_scores.units.setdefault(unit_id, UnitScore())
    score.numerator += numerator
    score.denominator += denominator
    score.rows += 1
    method_scores.raw_rows += 1


def load_jsonl_score_rows(repo_root: Path, discovery: dict[str, Any], warnings: list[str]) -> dict[str, MethodScores]:
    source_ref = discovery.get("source_ref")
    files: list[Path | str]
    if source_ref:
        files = git_ls(source_ref, discovery["glob"])
        git_batch_load(source_ref, [str(path) for path in files])
    else:
        files = sorted(Path(p) for p in repo_root.glob(discovery["glob"]))
    if not files:
        warnings.append(f"No files matched {discovery['glob']!r}")
        return {}

    unit_key = discovery["unit_key"]
    numerator_key = discovery["numerator_key"]
    denominator_key = discovery["denominator_key"]
    regex = discovery["method_name_regex"]
    template = discovery.get("method_name_template")
    out: dict[str, MethodScores] = {}

    for path in files:
        method = derive_method(path, regex, template)
        method_scores = out.setdefault(method, MethodScores(method=method))
        method_scores.source_files.add(source_id(source_ref, path))
        rows = (
            read_jsonl_text(git_text(source_ref, str(path)), source_id(source_ref, path))
            if source_ref
            else read_jsonl(path)  # type: ignore[arg-type]
        )
        for row in rows:
            try:
                unit_id = str(get_value(row, unit_key))
                numerator = to_float(get_value(row, numerator_key), path=source_id(source_ref, path), key=numerator_key)
                denominator = to_float(get_value(row, denominator_key), path=source_id(source_ref, path), key=denominator_key)
            except KeyError as exc:
                raise KeyError(f"{path}: missing key {exc.args[0]!r}") from exc
            add_unit_score(method_scores, unit_id, numerator, denominator)
    return out


def load_csv_score_rows(repo_root: Path, discovery: dict[str, Any], warnings: list[str]) -> dict[str, MethodScores]:
    source_ref = discovery.get("source_ref")
    files: list[Path | str]
    if source_ref:
        files = git_ls(source_ref, discovery["glob"])
        git_batch_load(source_ref, [str(path) for path in files])
    else:
        files = sorted(Path(p) for p in repo_root.glob(discovery["glob"]))
    if not files:
        warnings.append(f"No files matched {discovery['glob']!r}")
        return {}

    unit_key = discovery["unit_key"]
    numerator_key = discovery["numerator_key"]
    denominator_key = discovery["denominator_key"]
    regex = discovery["method_name_regex"]
    template = discovery.get("method_name_template")
    out: dict[str, MethodScores] = {}

    for path in files:
        method = derive_method(path, regex, template)
        method_scores = out.setdefault(method, MethodScores(method=method))
        method_scores.source_files.add(source_id(source_ref, path))
        if source_ref:
            handle = io.StringIO(git_text(source_ref, str(path)))
        else:
            handle = path.open("r", encoding="utf-8", newline="")  # type: ignore[union-attr]
        with handle:
            reader = csv.DictReader(handle)
            for row in reader:
                unit_id = str(row[unit_key])
                numerator = to_float(row[numerator_key], path=source_id(source_ref, path), key=numerator_key)
                denominator = to_float(row[denominator_key], path=source_id(source_ref, path), key=denominator_key)
                add_unit_score(method_scores, unit_id, numerator, denominator)
    return out


def load_json_score_files(repo_root: Path, discovery: dict[str, Any], warnings: list[str]) -> dict[str, MethodScores]:
    source_ref = discovery.get("source_ref")
    files: list[Path | str]
    if source_ref:
        files = git_ls(source_ref, discovery["glob"])
        git_batch_load(source_ref, [str(path) for path in files])
    else:
        files = sorted(Path(p) for p in repo_root.glob(discovery["glob"]))
    if not files:
        warnings.append(f"No files matched {discovery['glob']!r}")
        return {}

    numerator_key = discovery["numerator_key"]
    denominator_key = discovery["denominator_key"]
    regex = discovery["method_name_regex"]
    template = discovery.get("method_name_template")
    unit_key = discovery.get("unit_key")
    unit_id_from = discovery.get("unit_id_from")
    out: dict[str, MethodScores] = {}

    for path in files:
        method = derive_method(path, regex, template)
        method_scores = out.setdefault(method, MethodScores(method=method))
        method_scores.source_files.add(source_id(source_ref, path))
        row = (
            read_json_text(git_text(source_ref, str(path)), source_id(source_ref, path))
            if source_ref
            else read_json(path)  # type: ignore[arg-type]
        )
        if unit_id_from == "filename_stem":
            unit_id = Path(str(path)).stem
        elif unit_key:
            unit_id = str(get_value(row, unit_key))
        else:
            raise ValueError("json_score_files discovery requires unit_key or unit_id_from=filename_stem")
        numerator = to_float(get_value(row, numerator_key), path=source_id(source_ref, path), key=numerator_key)
        denominator = to_float(get_value(row, denominator_key), path=source_id(source_ref, path), key=denominator_key)
        add_unit_score(method_scores, unit_id, numerator, denominator)
    return out


def load_method_summary_results(repo_root: Path, discovery: dict[str, Any], warnings: list[str]) -> dict[str, MethodScores]:
    source_ref = discovery.get("source_ref")
    files: list[Path | str]
    if source_ref:
        files = git_ls(source_ref, discovery["glob"])
        git_batch_load(source_ref, [str(path) for path in files])
    else:
        files = sorted(Path(p) for p in repo_root.glob(discovery["glob"]))
    if not files:
        warnings.append(f"No files matched {discovery['glob']!r}")
        return {}

    regex = discovery["method_name_regex"]
    template = discovery.get("method_name_template")
    unit_key = discovery.get("unit_key", "chart_id")
    numerator_key = discovery.get("numerator_key", "score.correct")
    denominator_key = discovery.get("denominator_key", "score.total")
    results_key = discovery.get("results_key", "results")
    out: dict[str, MethodScores] = {}

    for path in files:
        method = derive_method(path, regex, template)
        method_scores = out.setdefault(method, MethodScores(method=method))
        method_scores.source_files.add(source_id(source_ref, path))
        summary = (
            read_json_text(git_text(source_ref, str(path)), source_id(source_ref, path))
            if source_ref
            else read_json(path)  # type: ignore[arg-type]
        )
        try:
            rows = get_value(summary, results_key)
        except KeyError as exc:
            raise KeyError(f"{path}: missing key {results_key!r}") from exc
        if not isinstance(rows, list):
            raise ValueError(f"{path}: key {results_key!r} must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{path}: every {results_key!r} item must be an object")
            try:
                unit_id = str(get_value(row, unit_key))
                numerator = to_float(get_value(row, numerator_key), path=source_id(source_ref, path), key=numerator_key)
                denominator = to_float(get_value(row, denominator_key), path=source_id(source_ref, path), key=denominator_key)
            except KeyError as exc:
                raise KeyError(f"{path}: missing key {exc.args[0]!r} in {results_key!r}") from exc
            add_unit_score(method_scores, unit_id, numerator, denominator)
    return out


def row_matches_filter(row: dict[str, Any], filter_spec: dict[str, Any] | None) -> bool:
    if not filter_spec:
        return True
    for key, expected in filter_spec.items():
        try:
            actual = get_value(row, key)
        except KeyError:
            return False
        if actual != expected:
            return False
    return True


def load_experiment6_cases_predictions(
    repo_root: Path,
    discovery: dict[str, Any],
    case_filter: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, MethodScores]:
    source_ref = discovery.get("source_ref")
    cases_path = repo_root / discovery["cases_jsonl"]
    if source_ref:
        git_batch_load(source_ref, [discovery["cases_jsonl"]])
        case_rows = read_jsonl_text(
            git_text(source_ref, discovery["cases_jsonl"]),
            source_id(source_ref, discovery["cases_jsonl"]),
        )
    else:
        if not cases_path.exists():
            warnings.append(f"Experiment 6 cases file does not exist: {discovery['cases_jsonl']}")
            return {}
        case_rows = read_jsonl(cases_path)

    cases = [row for row in case_rows if row_matches_filter(row, case_filter)]
    if not cases:
        warnings.append(f"No Experiment 6 cases remained after filter for {discovery['cases_jsonl']}")
        return {}

    prediction_files: list[Path | str]
    if "prediction_paths" in discovery:
        prediction_files = list(discovery["prediction_paths"])
    elif source_ref:
        prediction_files = git_ls(source_ref, discovery["prediction_glob"]) if "prediction_glob" in discovery else []
    else:
        prediction_files = sorted(Path(p) for p in repo_root.glob(discovery["prediction_glob"])) if "prediction_glob" in discovery else []
    synthetic_controls = discovery.get("synthetic_controls", [])
    if not prediction_files and not synthetic_controls:
        warnings.append(f"No Experiment 6 prediction files matched discovery for {discovery!r}")
        return {}
    if source_ref:
        git_batch_load(source_ref, [str(path) for path in prediction_files])

    regex = discovery["method_name_regex"]
    template = discovery.get("method_name_template")
    case_id_key = discovery.get("case_id_key", "verification_case_id")
    unit_key = discovery.get("unit_key", "chart_id")
    out: dict[str, MethodScores] = {}

    for control in synthetic_controls:
        method = str(control["method"])
        rule = str(control["rule"])
        method_scores = out.setdefault(method, MethodScores(method=method))
        method_scores.source_files.add(source_id(source_ref, discovery["cases_jsonl"]))
        method_scores.source_files.add(f"synthetic_control:{rule}")
        for case in cases:
            unit_id = str(get_value(case, unit_key))
            gold_consistent = bool(get_value(case, "label.consistent"))
            if rule == "all_accept":
                correct = 1.0 if gold_consistent else 0.0
            elif rule == "all_reject":
                correct = 0.0 if gold_consistent else 1.0
            elif rule == "oracle_label":
                correct = 1.0
            else:
                raise ValueError(f"Unsupported Experiment 6 synthetic control rule: {rule!r}")
            add_unit_score(method_scores, unit_id, correct, 1.0)

    for pred_path in prediction_files:
        method = derive_method(pred_path, regex, template)
        method_scores = out.setdefault(method, MethodScores(method=method))
        method_scores.source_files.add(source_id(source_ref, pred_path))
        pred_rows = (
            read_jsonl_text(git_text(source_ref, str(pred_path)), source_id(source_ref, pred_path))
            if source_ref
            else read_jsonl(pred_path)  # type: ignore[arg-type]
        )
        preds = {str(get_value(row, case_id_key)): row for row in pred_rows}
        for case in cases:
            case_id = str(get_value(case, case_id_key))
            unit_id = str(get_value(case, unit_key))
            gold_consistent = bool(get_value(case, "label.consistent"))
            pred_row = preds.get(case_id)
            correct = 0.0
            if pred_row is not None and pred_row.get("parse_ok") and pred_row.get("parsed_output") is not None:
                pred_consistent = bool(get_value(pred_row, "parsed_output.consistent"))
                correct = 1.0 if pred_consistent == gold_consistent else 0.0
            add_unit_score(method_scores, unit_id, correct, 1.0)
    return out


def merge_methods(dst: dict[str, MethodScores], src: dict[str, MethodScores]) -> None:
    for method, incoming in src.items():
        target = dst.setdefault(method, MethodScores(method=method))
        target.source_files.update(incoming.source_files)
        target.raw_rows += incoming.raw_rows
        for unit_id, score in incoming.units.items():
            current = target.units.setdefault(unit_id, UnitScore())
            current.numerator += score.numerator
            current.denominator += score.denominator
            current.rows += score.rows


def apply_method_aliases(methods: dict[str, MethodScores], aliases: dict[str, str]) -> dict[str, MethodScores]:
    if not aliases:
        return methods
    out: dict[str, MethodScores] = {}
    for method, scores in methods.items():
        target_name = aliases.get(method, method)
        target = out.setdefault(target_name, MethodScores(method=target_name))
        target.source_files.update(scores.source_files)
        target.raw_rows += scores.raw_rows
        for unit_id, score in scores.units.items():
            current = target.units.setdefault(unit_id, UnitScore())
            current.numerator += score.numerator
            current.denominator += score.denominator
            current.rows += score.rows
            current.filled_missing = current.filled_missing or score.filled_missing
    return out


def filter_methods(
    methods: dict[str, MethodScores],
    analysis: dict[str, Any],
    warnings: list[str],
) -> dict[str, MethodScores]:
    include_methods = set(analysis.get("include_methods", []))
    exclude_methods = set(analysis.get("exclude_methods", []))
    filtered = dict(methods)
    if include_methods:
        dropped = sorted(set(filtered) - include_methods)
        filtered = {method: scores for method, scores in filtered.items() if method in include_methods}
        if dropped:
            warnings.append(f"Dropped {len(dropped)} non-included methods: {', '.join(dropped[:12])}")
    if exclude_methods:
        dropped = sorted(method for method in filtered if method in exclude_methods)
        filtered = {method: scores for method, scores in filtered.items() if method not in exclude_methods}
        if dropped:
            warnings.append(f"Dropped excluded methods: {', '.join(dropped)}")

    required_methods = set(analysis.get("required_methods", []))
    missing_required = sorted(required_methods - set(filtered))
    if missing_required:
        raise ValueError(
            "Analysis set is missing required final methods: "
            + ", ".join(missing_required)
            + ". This usually means the config is pointing at a non-final run or a final per-sample artifact is absent."
        )
    return filtered


def load_methods(repo_root: Path, analysis: dict[str, Any], warnings: list[str]) -> dict[str, MethodScores]:
    methods: dict[str, MethodScores] = {}
    for discovery in analysis.get("method_discovery", []):
        fmt = discovery["format"]
        if fmt == "jsonl_score_rows":
            merge_methods(methods, load_jsonl_score_rows(repo_root, discovery, warnings))
        elif fmt == "csv_score_rows":
            merge_methods(methods, load_csv_score_rows(repo_root, discovery, warnings))
        elif fmt == "json_score_files":
            merge_methods(methods, load_json_score_files(repo_root, discovery, warnings))
        elif fmt == "method_summary_results":
            merge_methods(methods, load_method_summary_results(repo_root, discovery, warnings))
        elif fmt == "experiment6_verification_cases_predictions":
            merge_methods(
                methods,
                load_experiment6_cases_predictions(repo_root, discovery, analysis.get("case_filter"), warnings),
            )
        else:
            raise ValueError(f"Unsupported discovery format: {fmt}")
    methods = apply_method_aliases(methods, analysis.get("method_aliases", {}))
    return filter_methods(methods, analysis, warnings)


def load_unit_totals(repo_root: Path, source: dict[str, Any] | None, warnings: list[str]) -> dict[str, float]:
    if not source:
        return {}
    fmt = source["format"]
    totals: dict[str, float] = {}
    if fmt != "jsonl_score_rows":
        raise ValueError(f"Unsupported unit_total_source format: {fmt}")
    source_ref = source.get("source_ref")
    path = repo_root / source["path"]
    if source_ref:
        git_batch_load(source_ref, [source["path"]])
        rows = read_jsonl_text(git_text(source_ref, source["path"]), source_id(source_ref, source["path"]))
    elif not path.exists():
        warnings.append(f"unit_total_source does not exist: {source['path']}")
        return {}
    else:
        rows = read_jsonl(path)
    unit_key = source["unit_key"]
    denominator_key = source["denominator_key"]
    for row in rows:
        unit_id = str(get_value(row, unit_key))
        denominator = to_float(
            get_value(row, denominator_key),
            path=source_id(source_ref, source["path"]) if source_ref else path,
            key=denominator_key,
        )
        if unit_id in totals and totals[unit_id] != denominator:
            warnings.append(f"unit_total_source duplicate unit {unit_id} has differing denominators")
        totals[unit_id] = denominator
    return totals


def apply_missing_policy(
    methods: dict[str, MethodScores],
    unit_totals: dict[str, float],
    policy: str,
    warnings: list[str],
) -> list[str]:
    if unit_totals:
        analysis_units = sorted(unit_totals)
    else:
        unit_set: set[str] = set()
        for method_scores in methods.values():
            unit_set.update(method_scores.units)
        analysis_units = sorted(unit_set)

    if not analysis_units:
        raise ValueError("No analysis units available")

    for method, method_scores in sorted(methods.items()):
        missing = [unit_id for unit_id in analysis_units if unit_id not in method_scores.units]
        if not missing:
            continue
        if policy == "zero_correct_with_unit_total" and unit_totals:
            for unit_id in missing:
                method_scores.units[unit_id] = UnitScore(
                    numerator=0.0,
                    denominator=unit_totals[unit_id],
                    rows=0,
                    filled_missing=True,
                )
            warnings.append(f"{method}: filled {len(missing)} missing units as zero-correct using unit_total_source")
        elif policy == "strict_error":
            preview = ", ".join(missing[:5])
            raise ValueError(f"{method}: missing {len(missing)} units under strict_error policy: {preview}")
        else:
            warnings.append(f"{method}: missing {len(missing)} units; estimates use available units only")

    return analysis_units


def point_estimate(method_scores: MethodScores, units: list[str]) -> tuple[float, float, float]:
    numerator = 0.0
    denominator = 0.0
    for unit_id in units:
        score = method_scores.units.get(unit_id)
        if score is None:
            continue
        numerator += score.numerator
        denominator += score.denominator
    estimate = numerator / denominator if denominator > 0 else float("nan")
    return numerator, denominator, estimate


def method_arrays(method_scores: MethodScores, units: list[str]) -> tuple[list[float], list[float]]:
    numerators: list[float] = []
    denominators: list[float] = []
    for unit_id in units:
        score = method_scores.units.get(unit_id, UnitScore())
        numerators.append(score.numerator)
        denominators.append(score.denominator)
    return numerators, denominators


def build_pairs(methods: list[str], pair_spec: Any) -> list[tuple[str, str]]:
    if pair_spec == "all_pairs" or pair_spec is None:
        pairs: list[tuple[str, str]] = []
        for i, method_a in enumerate(methods):
            for method_b in methods[i + 1 :]:
                pairs.append((method_a, method_b))
        return pairs
    if not isinstance(pair_spec, list):
        raise ValueError("paired_comparisons must be 'all_pairs' or a list")
    pairs = []
    for item in pair_spec:
        if isinstance(item, dict):
            method_a = item.get("method_a") or item.get("challenger")
            method_b = item.get("method_b") or item.get("baseline")
        else:
            method_a, method_b = item
        if not method_a or not method_b:
            raise ValueError(f"Invalid paired comparison: {item!r}")
        pairs.append((str(method_a), str(method_b)))
    return pairs


def run_bootstrap(
    methods: dict[str, MethodScores],
    units: list[str],
    iterations: int,
    seed: int,
    confidence_level: float,
    pair_spec: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    method_names = sorted(methods)
    arrays = {name: method_arrays(methods[name], units) for name in method_names}
    method_samples: dict[str, list[float]] = {name: [] for name in method_names}
    pairs = [(a, b) for a, b in build_pairs(method_names, pair_spec) if a in methods and b in methods]
    pair_samples: dict[tuple[str, str], list[float]] = {pair: [] for pair in pairs}
    n = len(units)

    for _ in range(iterations):
        indices = [rng.randrange(n) for _ in range(n)]
        values: dict[str, float] = {}
        for name, (numerators, denominators) in arrays.items():
            value = metric(numerators, denominators, indices)
            if value is None:
                continue
            values[name] = value
            method_samples[name].append(value)
        for method_a, method_b in pairs:
            if method_a in values and method_b in values:
                pair_samples[(method_a, method_b)].append(values[method_a] - values[method_b])

    alpha = 1.0 - confidence_level
    lo_q = alpha / 2.0
    hi_q = 1.0 - alpha / 2.0

    estimates: list[dict[str, Any]] = []
    for name in method_names:
        numerator, denominator, estimate = point_estimate(methods[name], units)
        filled = sum(1 for unit_id in units if methods[name].units.get(unit_id, UnitScore()).filled_missing)
        observed = sum(1 for unit_id in units if unit_id in methods[name].units and not methods[name].units[unit_id].filled_missing)
        estimates.append(
            {
                "method": name,
                "n_units": len(units),
                "observed_units": observed,
                "filled_missing_units": filled,
                "score_numerator": numerator,
                "score_denominator": denominator,
                "point_estimate": estimate,
                "ci_lower": percentile(method_samples[name], lo_q),
                "ci_upper": percentile(method_samples[name], hi_q),
                "bootstrap_samples": len(method_samples[name]),
                "source_files": sorted(methods[name].source_files),
                "raw_rows": methods[name].raw_rows,
            }
        )

    deltas: list[dict[str, Any]] = []
    for method_a, method_b in pairs:
        _, _, estimate_a = point_estimate(methods[method_a], units)
        _, _, estimate_b = point_estimate(methods[method_b], units)
        samples = pair_samples[(method_a, method_b)]
        deltas.append(
            {
                "method_a": method_a,
                "method_b": method_b,
                "delta_definition": "method_a - method_b",
                "point_delta": estimate_a - estimate_b,
                "ci_lower": percentile(samples, lo_q),
                "ci_upper": percentile(samples, hi_q),
                "bootstrap_samples": len(samples),
            }
        )

    return estimates, deltas


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/bootstrap_paired_delta_policy.json")
    parser.add_argument("--analysis-set", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    config_path = (REPO_ROOT / args.config).resolve()
    config = read_json(config_path)
    analysis_sets = config.get("analysis_sets", {})
    if args.analysis_set not in analysis_sets:
        available = ", ".join(sorted(analysis_sets))
        raise SystemExit(f"Unknown analysis set {args.analysis_set!r}. Available: {available}")
    analysis = analysis_sets[args.analysis_set]
    defaults = config["frozen_defaults"]
    iterations = args.iterations if args.iterations is not None else int(defaults["bootstrap_iterations"])
    seed = args.seed if args.seed is not None else int(defaults["seed"])
    confidence_level = float(defaults["confidence_level"])
    if iterations <= 0:
        raise SystemExit("--iterations must be positive")
    if not 0 < confidence_level < 1:
        raise SystemExit("confidence_level must be between 0 and 1")

    warnings: list[str] = []
    methods = load_methods(REPO_ROOT, analysis, warnings)
    if not methods:
        raise SystemExit(f"No method score inputs were found for analysis set {args.analysis_set!r}")

    unit_totals = load_unit_totals(REPO_ROOT, analysis.get("unit_total_source"), warnings)
    units = apply_missing_policy(methods, unit_totals, analysis.get("missing_unit_policy", "strict_error"), warnings)
    estimates, deltas = run_bootstrap(
        methods,
        units,
        iterations,
        seed,
        confidence_level,
        analysis.get("paired_comparisons"),
    )

    output_dir = REPO_ROOT / (args.output_dir or analysis["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    write_json(output_dir / "point_estimates.json", estimates)
    write_json(output_dir / "paired_deltas.json", deltas)
    write_csv(
        output_dir / "point_estimates.csv",
        estimates,
        [
            "method",
            "n_units",
            "observed_units",
            "filled_missing_units",
            "score_numerator",
            "score_denominator",
            "point_estimate",
            "ci_lower",
            "ci_upper",
            "bootstrap_samples",
            "raw_rows",
        ],
    )
    write_csv(
        output_dir / "paired_deltas.csv",
        deltas,
        ["method_a", "method_b", "delta_definition", "point_delta", "ci_lower", "ci_upper", "bootstrap_samples"],
    )

    input_files = sorted({file for method in methods.values() for file in method.source_files})
    manifest = {
        "analysis_set": args.analysis_set,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": rel(config_path),
        "config_sha256": sha256(config_path),
        "policy_document": config.get("policy_document"),
        "script_path": rel(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "bootstrap_iterations": iterations,
        "seed": seed,
        "confidence_level": confidence_level,
        "interval_method": defaults.get("interval_method"),
        "resampling_unit": defaults.get("resampling_unit"),
        "metric_definition": defaults.get("metric_definition"),
        "paired_delta_definition": defaults.get("paired_delta_definition"),
        "n_methods": len(methods),
        "n_units": len(units),
        "methods": sorted(methods),
        "input_files": [
            {"path": file, "sha256": digest}
            for file in input_files
            for digest in [source_sha256(file)]
            if digest is not None
        ],
        "warnings": warnings,
        "outputs": {
            "point_estimates_json": rel(output_dir / "point_estimates.json"),
            "point_estimates_csv": rel(output_dir / "point_estimates.csv"),
            "paired_deltas_json": rel(output_dir / "paired_deltas.json"),
            "paired_deltas_csv": rel(output_dir / "paired_deltas.csv"),
        },
    }
    write_json(output_dir / "bootstrap_run_manifest.json", manifest)

    print(json.dumps({"analysis_set": args.analysis_set, "output_dir": rel(output_dir), "warnings": warnings}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
