#!/usr/bin/env python3
"""Create a short Actions summary from captured HeadlessMC output."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
from pathlib import Path
from typing import Any


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            return list(csv.DictReader(source))
    except FileNotFoundError:
        return []


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}" if isinstance(value, float) else str(value)
    return str(value)


def run_summary(directory: Path) -> dict[str, Any]:
    state = read_json(directory / "run-state.json") or {}
    world = read_json(directory / "logs" / "headless-world-report.json") or {}
    smoke = read_json(directory / "logs" / "headless-smoke-report.json") or {}
    ticks = read_csv(directory / "logs" / "headless-world-ticks.csv")
    intervals = [float(row["tick_interval_ms"]) for row in ticks if row.get("tick_interval_ms")]
    work = [float(row["tick_work_ms"]) for row in ticks if row.get("tick_work_ms")]
    memory = read_csv(directory / "logs" / "headless-world-memory.csv")
    host = read_csv(directory / "host-metrics.csv")
    host_rss = [float(row["max_java_rss_mb"]) for row in host if row.get("max_java_rss_mb")]
    host_available = [float(row["host_mem_available_mb"]) for row in host if row.get("host_mem_available_mb")]
    errors: list[str] = []
    latest = directory / "logs" / "latest.log"
    if latest.is_file():
        for line in latest.read_text(encoding="utf-8", errors="replace").splitlines():
            if any(token in line for token in ("[ERROR]", "[FATAL]", "Exception", "crash report", "Test failed")):
                errors.append(line[-500:])
        errors = errors[-8:]
    crash_reports = sorted((directory / "crash-reports").glob("*.txt")) if (directory / "crash-reports").is_dir() else []
    return {
        "label": directory.name,
        "action_outcome": state.get("action_outcome", "unknown"),
        "world": world,
        "smoke": smoke,
        "tick_count": len(intervals),
        "tick_interval_ms": {
            "mean": statistics.fmean(intervals) if intervals else None,
            "p50": percentile(intervals, 0.50),
            "p95": percentile(intervals, 0.95),
            "p99": percentile(intervals, 0.99),
            "max": max(intervals) if intervals else None,
            "over_50ms_pct": (sum(value > 50.0 for value in intervals) * 100.0 / len(intervals)) if intervals else None,
        },
        "tick_work_ms": {
            "mean": statistics.fmean(work) if work else None,
            "p50": percentile(work, 0.50),
            "p95": percentile(work, 0.95),
            "p99": percentile(work, 0.99),
            "max": max(work) if work else None,
        },
        "sampled_memory_rows": len(memory),
        "host_samples": len(host),
        "max_java_rss_mb": max(host_rss) if host_rss else None,
        "min_host_available_mb": min(host_available) if host_available else None,
        "crash_reports": len(crash_reports),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--level", required=True)
    parser.add_argument("--target-ref", default="")
    parser.add_argument("--commit", default="")
    parser.add_argument("--experiment", default="none")
    parser.add_argument("--manifest-status", default="unknown")
    parser.add_argument("--lock-status", default="unknown")
    parser.add_argument("--repository-test-status", default="unknown")
    parser.add_argument("--build-status", default="skipped")
    args = parser.parse_args()

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    runs = [run_summary(path) for path in sorted(root.iterdir()) if path.is_dir() and (path / "run-state.json").is_file()]
    lines = [
        "# Boundless HeadlessMC run",
        "",
        f"- **Runner:** `ubuntu-latest` (Linux CI benchmark; not equivalent to Windows hardware measurements)",
        f"- **Level:** `{args.level}`",
        f"- **Target:** `{args.target_ref or 'current workflow ref'}` (`{args.commit or 'unknown commit'}`)",
        f"- **Better Chunk Loading experiment:** `{args.experiment}`",
        "- **Runtime:** Minecraft 1.20.1 · Forge 47.4.28 expected · Java 17 · HeadlessMC 3.0.0-RC9 · MC-Runtime-Test 5.0.1",
        f"- **Preflight:** manifest `{args.manifest_status}` · dependency lock `{args.lock_status}` · repository tests `{args.repository_test_status}` · mod build `{args.build_status}`",
        "",
    ]

    if runs:
        lines.extend([
            "## Runtime passes",
            "",
            "| Pass | Action | Forge | BCL prediction | Seed | Loaded mods | World ticks | Travel (blocks) | Tick work p95 / p99 (ms) | Tick interval p95 (ms) | Max Java RSS (MB) | Crashes |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for result in runs:
            world = result["world"]
            interval = result["tick_interval_ms"]
            lines.append(
                f"| {result['label']} | {result['action_outcome']} | "
                f"{fmt(result['smoke'].get('forge_version'))} | "
                f"{fmt(world.get('enable_prediction'))} | {fmt(world.get('seed'))} | "
                f"{fmt(world.get('loaded_mod_count'))} | {fmt(world.get('server_ticks_sampled'))} | "
                f"{fmt(world.get('player_travel_blocks'))} | "
                f"{fmt(result['tick_work_ms']['p95'])} / {fmt(result['tick_work_ms']['p99'])} | "
                f"{fmt(interval['p95'])} | {fmt(result['max_java_rss_mb'])} | {result['crash_reports']} |"
            )
        lines.append("")
        lines.append("`tick_work_ms` is the measured server tick START-to-END work interval (an MSPT proxy); `tick_interval_ms` also includes normal 20 TPS pacing.")
        lines.append("")
        errors = [(run["label"], line) for run in runs for line in run["errors"]]
        if errors:
            lines.extend(["## Log signals", ""])
            lines.extend(f"- `{label}` — `{line.replace('`', '\\`')}`" for label, line in errors[:12])
            lines.append("")
    else:
        lines.extend(["No runtime pass produced artifacts. See the failed setup/build steps above.", ""])

    lines.extend([
        "## Artifacts",
        "",
        "The attached artifact contains the launcher/game logs, crash reports, GC log, JFR recording, input mod hashes, and available world/runner metrics.",
        "",
        "For A/B results, compare only passes with the same seed and workload. These numbers describe the GitHub Linux runner; do not combine them with the Windows-machine baselines.",
        "",
    ])
    report = "\n".join(lines)
    (root / "report.md").write_text(report, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as destination:
            destination.write(report)
    print(report)


if __name__ == "__main__":
    main()
