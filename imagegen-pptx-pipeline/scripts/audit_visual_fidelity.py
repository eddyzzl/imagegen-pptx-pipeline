#!/usr/bin/env python3
"""Audit rendered PPTX previews against approved slide comps."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_POLICY = {
    "enabled": True,
    "report_path": "qa/pptx-visual-fidelity-audit.json",
    "summary_fallback_path": "qa/manual-visual-diff/visual_diff_summary.json",
    "active_manual_visual_diff_summary_path": "qa/manual-visual-diff/visual_diff_summary.json",
    "require_all_output_lanes_pass": True,
    "require_report_source_sha256": True,
    "require_output_pptx_sha256": True,
    "forbid_pixel_locked_summary_sources": True,
    "max_avg_mean_abs": 14.0,
    "max_slide_mean_abs": 20.0,
    "max_avg_pixel_diff_pct_over_24": 8.0,
    "max_slide_pixel_diff_pct_over_24": 12.0,
}


def as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"visual fidelity input does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def normalize_entries(payload: dict) -> list[dict]:
    if isinstance(payload.get("summary"), list):
        return payload["summary"]
    if isinstance(payload.get("lanes"), list):
        return payload["lanes"]
    if isinstance(payload.get("outputs"), list):
        return payload["outputs"]
    if "lane" in payload or "avg_mean_abs" in payload or "slides" in payload:
        return [payload]
    return []


def fill_derived_metrics(entry: dict) -> dict:
    entry = dict(entry)
    slides = entry.get("slides")
    if isinstance(slides, list) and slides:
        mean_abs_values = [as_float(slide.get("mean_abs")) for slide in slides if isinstance(slide, dict)]
        diff_values = [
            as_float(slide.get("pixel_diff_pct_over_24"))
            for slide in slides
            if isinstance(slide, dict)
        ]
        if mean_abs_values:
            entry.setdefault("avg_mean_abs", sum(mean_abs_values) / len(mean_abs_values))
            entry.setdefault("max_mean_abs", max(mean_abs_values))
        if diff_values:
            entry.setdefault("avg_pixel_diff_pct_over_24", sum(diff_values) / len(diff_values))
            entry.setdefault("max_pixel_diff_pct_over_24", max(diff_values))
    return entry


def output_pptx_records(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"output PPTX does not exist: {resolved}")
        records.append(
            {
                "path": str(resolved),
                "sha256": file_sha256(resolved),
                "bytes": resolved.stat().st_size,
            }
        )
    return records


def evaluate(entries: list[dict], policy: dict, summary_path: Path, output_pptx: list[Path]) -> dict:
    failures: list[str] = []
    results: list[dict] = []
    if not entries:
        failures.append("visual fidelity report contains no output lanes or slides")

    for idx, raw_entry in enumerate(entries, 1):
        entry = fill_derived_metrics(raw_entry)
        lane = entry.get("lane") or entry.get("style_lane_id") or entry.get("output_id") or f"entry-{idx}"
        lane_failures: list[str] = []
        checks = [
            ("avg_mean_abs", "max_avg_mean_abs"),
            ("max_mean_abs", "max_slide_mean_abs"),
            ("avg_pixel_diff_pct_over_24", "max_avg_pixel_diff_pct_over_24"),
            ("max_pixel_diff_pct_over_24", "max_slide_pixel_diff_pct_over_24"),
        ]
        for metric_key, threshold_key in checks:
            value = as_float(entry.get(metric_key))
            threshold = as_float(policy.get(threshold_key), as_float(DEFAULT_POLICY[threshold_key]))
            if value > threshold:
                lane_failures.append(f"{metric_key} {value:.2f} exceeds {threshold_key} {threshold:.2f}")
        if lane_failures:
            failures.extend(f"{lane}: {failure}" for failure in lane_failures)
        results.append(
            {
                "lane": lane,
                "status": "FAIL" if lane_failures else "PASS",
                "avg_mean_abs": round(as_float(entry.get("avg_mean_abs")), 2),
                "max_mean_abs": round(as_float(entry.get("max_mean_abs")), 2),
                "avg_pixel_diff_pct_over_24": round(as_float(entry.get("avg_pixel_diff_pct_over_24")), 2),
                "max_pixel_diff_pct_over_24": round(as_float(entry.get("max_pixel_diff_pct_over_24")), 2),
                "failures": lane_failures,
            }
        )

    return {
        "status": "FAIL" if failures else "PASS",
        "policy": policy,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_summary_path": str(summary_path),
        "source_summary_sha256": file_sha256(summary_path),
        "output_pptx": output_pptx_records(output_pptx),
        "outputs": results,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="visual_diff_summary.json or equivalent metrics report.")
    parser.add_argument("--policy", help="Optional JSON file containing pptx_visual_fidelity_policy.")
    parser.add_argument("--report", help="Optional output report JSON path.")
    parser.add_argument(
        "--output-pptx",
        action="append",
        default=[],
        help="Final PPTX path covered by this visual fidelity report. Repeat for multi-style outputs.",
    )
    args = parser.parse_args()

    try:
        summary_path = Path(args.summary).expanduser().resolve()
        payload = load_json(summary_path)
        policy = dict(DEFAULT_POLICY)
        if args.policy:
            policy_payload = load_json(Path(args.policy).expanduser().resolve())
            policy.update(policy_payload.get("pptx_visual_fidelity_policy") or policy_payload)
        report = evaluate(
            normalize_entries(payload),
            policy,
            summary_path,
            [Path(item) for item in args.output_pptx],
        )
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
