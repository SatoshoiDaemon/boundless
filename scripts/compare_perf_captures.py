"""Compare normalized Boundless performance captures without hiding configuration drift."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


FIELDS = [
    "run_id",
    "scenario",
    "commit",
    "mod_lock_sha256",
    "config_fingerprint_sha256",
    "shaderpack_sha256",
    "runtime_mod_count",
    "startup_timer_s",
    "menu_signal_s",
    "menu_ready_capture_elapsed_s",
    "integrated_server_start_s",
    "world_ready_s",
    "human_world_ready_capture_elapsed_s",
    "presentmon_scenario",
    "f3_point_fps",
    "f3_point_server_tick_ms",
    "mean_fps",
    "fps_1_percent_low",
    "fps_0_1_percent_low",
    "frametime_p95_ms",
    "frametime_p99_ms",
    "spark_mean_tps",
    "spark_average_mspt",
    "spark_p95_mspt",
    "spark_p99_mspt",
    "boundless_mean_time_tps_equivalent",
    "boundless_average_mspt",
    "boundless_p50_mspt",
    "boundless_p95_mspt",
    "boundless_p99_mspt",
    "boundless_max_mspt",
    "tick_backlog_warning_p95_ms",
    "tick_backlog_warning_max_ms",
    "jfr_tick_window_average_p95_ms",
    "gc_pause_sum_s",
    "chunk_generation_events",
    "jfr_server_thread_samples",
]


def fingerprint_config(inventory: dict[str, Any]) -> str:
    files = inventory.get("configFingerprints") or []
    shader = inventory.get("selectedShaderPackSha256") or ""
    if not files and not shader:
        return ""
    canonical = "\n".join(
        f"{item.get('file', '')}:{item.get('sha256', '')}"
        for item in sorted(files, key=lambda entry: entry.get("file", ""))
    )
    return hashlib.sha256(f"{canonical}\nshader:{shader}".encode("utf-8")).hexdigest()


def mod_lock_hash(run_directory: Path, inventory: dict[str, Any]) -> str:
    lock_path = run_directory / (inventory.get("modLock") or "mod-lock.csv")
    if not lock_path.exists():
        return ""
    return hashlib.sha256(lock_path.read_bytes()).hexdigest()


def blank_if_none(value: Any) -> Any:
    return "" if value is None else value


def load_row(run_directory: Path) -> dict[str, Any]:
    run_info = json.loads((run_directory / "run.json").read_text(encoding="utf-8-sig"))
    analysis = json.loads((run_directory / "analysis.json").read_text(encoding="utf-8-sig"))
    log = analysis.get("log") or {}
    present = (analysis.get("presentMon") or [{}])[0]
    phase_events = analysis.get("phaseEvents") or []
    menu_mark = next((event for event in phase_events if event.get("event") == "menu-ready"), {})
    world_mark = next((event for event in phase_events if event.get("event") == "world-ready"), {})
    jfr = analysis.get("jfr") or {}
    ticks = jfr.get("durationSampledServerTicks_ms") or {}
    gc = jfr.get("gc") or {}
    chunks = jfr.get("chunkGeneration") or {}
    server_samples = (jfr.get("executionSamples") or {}).get("Server thread") or {}
    spark_rows = analysis.get("sparkSamples") or []
    spark = spark_rows[-1] if spark_rows else {}
    tick_rows = analysis.get("tickSamples") or []
    tick = tick_rows[-1] if tick_rows else {}
    f3_rows = analysis.get("manualF3Samples") or []
    f3 = f3_rows[-1] if f3_rows else {}
    inventory = run_info.get("inventory") or {}
    row = {
        "run_id": run_info.get("runId", run_directory.name),
        "scenario": run_info.get("scenario", ""),
        "commit": (run_info.get("git") or {}).get("commit", ""),
        "mod_lock_sha256": mod_lock_hash(run_directory, inventory),
        "config_fingerprint_sha256": fingerprint_config(inventory),
        "shaderpack_sha256": inventory.get("selectedShaderPackSha256", ""),
        "runtime_mod_count": log.get("runtimeModCount", ""),
        "startup_timer_s": blank_if_none(log.get("minecraftStartupTimer_s")),
        "menu_signal_s": blank_if_none(log.get("firstMainMenuSignal_s")),
        "menu_ready_capture_elapsed_s": menu_mark.get("elapsed_s", ""),
        "integrated_server_start_s": log.get("integratedServerStart_s") or "",
        "world_ready_s": log.get("worldDoneMarker_sFromLaunch") or "",
        "human_world_ready_capture_elapsed_s": world_mark.get("elapsed_s", ""),
        "presentmon_scenario": present.get("scenario", ""),
        "f3_point_fps": f3.get("fps", ""),
        "f3_point_server_tick_ms": f3.get("server_tick_ms", ""),
        "mean_fps": present.get("meanFps", ""),
        "fps_1_percent_low": present.get("onePercentLowFps", ""),
        "fps_0_1_percent_low": present.get("zeroPointOnePercentLowFps", ""),
        "frametime_p95_ms": (present.get("frametimeMs") or {}).get("p95", ""),
        "frametime_p99_ms": (present.get("frametimeMs") or {}).get("p99", ""),
        "spark_mean_tps": spark.get("mean_tps", ""),
        "spark_average_mspt": spark.get("average_mspt", ""),
        "spark_p95_mspt": spark.get("p95_mspt", ""),
        "spark_p99_mspt": spark.get("p99_mspt", ""),
        "boundless_mean_time_tps_equivalent": tick.get("mean_tps", ""),
        "boundless_average_mspt": tick.get("average_mspt", ""),
        "boundless_p50_mspt": tick.get("p50_mspt", ""),
        "boundless_p95_mspt": tick.get("p95_mspt", ""),
        "boundless_p99_mspt": tick.get("p99_mspt", ""),
        "boundless_max_mspt": tick.get("max_mspt", ""),
        "tick_backlog_warning_p95_ms": blank_if_none((log.get("tickBacklogWarnings_ms") or {}).get("p95")),
        "tick_backlog_warning_max_ms": blank_if_none((log.get("tickBacklogWarnings_ms") or {}).get("max")),
        "jfr_tick_window_average_p95_ms": blank_if_none(ticks.get("p95")),
        "gc_pause_sum_s": blank_if_none(gc.get("pauseSecondsSumOfPauses")),
        "chunk_generation_events": blank_if_none(chunks.get("eventCount")),
        "jfr_server_thread_samples": blank_if_none(server_samples.get("sampleCount")),
    }
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directories", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("performance-comparison"))
    args = parser.parse_args()
    if len(args.run_directories) < 2:
        parser.error("provide at least two run directories")

    rows = [load_row(path.resolve()) for path in args.run_directories]
    reference = rows[0]
    for row in rows:
        row["scenario_matches_reference"] = row["scenario"] == reference["scenario"]
        reference_mod_count = reference.get("runtime_mod_count")
        row_mod_count = row.get("runtime_mod_count")
        if reference_mod_count and row_mod_count and reference_mod_count != row_mod_count:
            row["mods_match_reference"] = False
        elif reference["mod_lock_sha256"] and row["mod_lock_sha256"]:
            row["mods_match_reference"] = row["mod_lock_sha256"] == reference["mod_lock_sha256"]
        else:
            row["mods_match_reference"] = "unknown"
        if reference["config_fingerprint_sha256"] and row["config_fingerprint_sha256"]:
            row["config_matches_reference"] = row["config_fingerprint_sha256"] == reference["config_fingerprint_sha256"]
        else:
            row["config_matches_reference"] = "unknown"

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = FIELDS + ["scenario_matches_reference", "mods_match_reference", "config_matches_reference"]
    with (output_dir / "comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    preferred_table_fields = ["run_id", "runtime_mod_count", "startup_timer_s", "menu_signal_s", "menu_ready_capture_elapsed_s", "integrated_server_start_s", "world_ready_s", "presentmon_scenario", "mean_fps", "fps_1_percent_low", "fps_0_1_percent_low", "f3_point_fps", "f3_point_server_tick_ms", "spark_mean_tps", "spark_average_mspt", "spark_p95_mspt", "spark_p99_mspt", "boundless_mean_time_tps_equivalent", "boundless_p95_mspt", "boundless_p99_mspt", "tick_backlog_warning_p95_ms", "tick_backlog_warning_max_ms", "gc_pause_sum_s", "chunk_generation_events"]
    table_fields = [
        field for field in preferred_table_fields
        if field == "run_id" or any(row.get(field) not in (None, "") for row in rows)
    ]
    lines = ["# Boundless performance comparison", "", "| " + " | ".join(table_fields) + " |", "| " + " | ".join(["---"] * len(table_fields)) + " |"]
    def format_cell(value: Any) -> str:
        if value is None or value == "":
            return ""
        if isinstance(value, (int, float)):
            return f"{value:.3f}".rstrip("0").rstrip(".") if math.isfinite(value) else ""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{numeric:.3f}".rstrip("0").rstrip(".") if math.isfinite(numeric) else str(value)
    for row in rows:
        lines.append("| " + " | ".join(format_cell(row.get(field, "")) for field in table_fields) + " |")
    lines.extend(["", "## Match status", "", "| run_id | scenario_matches_reference | mods_match_reference | config_matches_reference |", "| --- | --- | --- | --- |"])
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in ["run_id", "scenario_matches_reference", "mods_match_reference", "config_matches_reference"]) + " |")
    lines.extend(["", "`false` marks a known scenario or runtime mod-count, JAR-hash, or configuration-fingerprint mismatch; `unknown` means the needed baseline lock was not retained. Startup timers are descriptive because the historical run has no JAR or configuration lock.", ""])
    (output_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_dir / 'comparison.csv'} and {output_dir / 'comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
