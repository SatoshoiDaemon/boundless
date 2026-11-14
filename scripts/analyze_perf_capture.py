"""Summarize Boundless logs, JFR recordings, Spark samples and PresentMon CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def duration_seconds(value: Any) -> float | None:
    """Convert the ISO-8601 durations emitted by `jfr print --json` to seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    if not value.startswith("P"):
        try:
            return float(value)
        except ValueError:
            return None

    match = re.fullmatch(
        r"P(?:(?P<days>[\d.]+)D)?(?:T(?:(?P<hours>[\d.]+)H)?(?:(?P<minutes>[\d.]+)M)?(?:(?P<seconds>[\d.]+)S)?)?",
        value,
    )
    if not match:
        return None
    parts = {key: float(item or 0) for key, item in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percent * len(ordered)) - 1))
    return ordered[index]


def stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "min": None, "p50": None, "p95": None, "p99": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "min": min(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_log(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    time_prefix = re.compile(r"^\[(?P<clock>\d{2}:\d{2}:\d{2})(?:\.\d+)?\]")
    severity_line = re.compile(r"\[[^\]]+/(?P<severity>WARN|ERROR)\]: (?P<message>.*)$")
    mod_count = re.compile(r"Loading (?P<count>\d+) mods:")
    startup_timer = re.compile(r"Game took (?P<seconds>[\d.]+) seconds to start")
    world_done = re.compile(r"Done \((?P<seconds>[\d.]+)s\)!")
    spawn_progress = re.compile(r"Preparing spawn area: (?P<percent>\d+)%")
    tick_behind = re.compile(
        r"Can't keep up! Is the server overloaded\? Running (?P<ms>[\d.]+)ms or (?P<ticks>[\d.]+) ticks behind"
    )
    deferred_task = re.compile(r"Mod '(?P<mod>[^']+)' took (?P<seconds>[\d.]+) s to run a deferred task")
    watchdog_tick = re.compile(r"A single server tick has taken (?P<ms>[\d.]+), more than (?P<limit>[\d.]+) milliseconds")
    resource_generation = re.compile(
        r"Finished runtime resources generation for (?P<packs>\d+) packs in a total of (?P<ms>[\d.]+) ms"
    )
    shader_sources = re.compile(r"Loaded (?P<count>\d+) shader sources in (?P<ms>[\d.]+) ms")
    shader_conflict = re.compile(
        r"Mod\(s\) \[(?P<mods>[^\]]+)\] are modifying Embeddium class (?P<target>.+?), which may cause instability\."
    )
    emi_reload = re.compile(r"\[EMI\] Reloaded EMI in (?P<ms>[\d.]+)ms")

    rows: list[dict[str, Any]] = []
    clock_events: list[tuple[int, str, dict[str, Any]]] = []
    conflicts: dict[str, set[str]] = defaultdict(set)
    deferred: list[dict[str, Any]] = []
    backlog_ms: list[float] = []
    backlog_ticks: list[float] = []
    spawn_values: list[tuple[int, int]] = []
    raw_event_count = 0
    startup_seconds: float | None = None
    runtime_mod_count: int | None = None
    world_done_seconds: float | None = None
    watchdog_ms: list[float] = []
    resources: list[dict[str, float]] = []
    shader_loads: list[dict[str, float]] = []
    emi_reload_ms: list[float] = []
    severity_counts: Counter[str] = Counter()
    error_messages: Counter[str] = Counter()

    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            severity_match = severity_line.search(line)
            if severity_match:
                severity = severity_match.group("severity").lower()
                severity_counts[severity] += 1
                if severity == "error":
                    error_messages[severity_match.group("message").strip()] += 1
            time_match = time_prefix.match(line)
            if not time_match:
                continue
            clock = time_match.group("clock")
            hours, minutes, seconds = (int(value) for value in clock.split(":"))
            clock_seconds = hours * 3600 + minutes * 60 + seconds
            event_name: str | None = None
            subject = ""
            value: float | int | str | None = None
            unit = ""

            if "ModLauncher running" in line:
                event_name = "modlauncher_start"
            if "Loading " in line:
                match = mod_count.search(line)
                if match:
                    runtime_mod_count = int(match.group("count"))
                    event_name, value, unit = "runtime_mod_count", runtime_mod_count, "mods"
            match = startup_timer.search(line)
            if match:
                startup_seconds = float(match.group("seconds"))
                event_name, value, unit = "minecraft_startup_timer", startup_seconds, "s"
            if "MAIN_MENU_" in line:
                event_name = "main_menu_signal"
                subject = "ReactiveMusic MAIN_MENU_ signal"
            if "Starting integrated minecraft server" in line:
                event_name = "integrated_server_start"
            if "Preparing level" in line:
                event_name = "world_prepare"
            match = world_done.search(line)
            if match:
                world_done_seconds = float(match.group("seconds"))
                event_name, value, unit = "world_done_marker", world_done_seconds, "s"
            match = spawn_progress.search(line)
            if match:
                progress = int(match.group("percent"))
                spawn_values.append((clock_seconds, progress))
                event_name, value, unit = "spawn_progress", progress, "%"
            match = tick_behind.search(line)
            if match:
                milliseconds = float(match.group("ms"))
                ticks = float(match.group("ticks"))
                backlog_ms.append(milliseconds)
                backlog_ticks.append(ticks)
                event_name, value, unit = "tick_backlog_warning", milliseconds, "ms"
                subject = f"{ticks:g} ticks behind"
            match = deferred_task.search(line)
            if match:
                elapsed = float(match.group("seconds"))
                task = {"clock": clock, "mod": match.group("mod"), "seconds": elapsed}
                deferred.append(task)
                event_name, subject, value, unit = "mod_deferred_task", task["mod"], elapsed, "s"
            match = watchdog_tick.search(line)
            if match:
                milliseconds = float(match.group("ms"))
                watchdog_ms.append(milliseconds)
                event_name, value, unit = "watchdog_tick", milliseconds, "ms"
            match = resource_generation.search(line)
            if match:
                resource = {"packs": int(match.group("packs")), "milliseconds": float(match.group("ms"))}
                resources.append(resource)
                event_name, subject, value, unit = "runtime_resource_generation", f"{resource['packs']} packs", resource["milliseconds"], "ms"
            match = shader_sources.search(line)
            if match:
                shader = {"sourceCount": int(match.group("count")), "milliseconds": float(match.group("ms"))}
                shader_loads.append(shader)
                event_name, subject, value, unit = "shader_source_load", f"{shader['sourceCount']} sources", shader["milliseconds"], "ms"
            match = shader_conflict.search(line)
            if match:
                mods = [item.strip() for item in match.group("mods").split(",")]
                target = match.group("target").strip()
                for mod in mods:
                    conflicts[target].add(mod)
                event_name, subject, value, unit = "embeddium_internal_modification", target, ";".join(mods), "mods"
            match = emi_reload.search(line)
            if match:
                milliseconds = float(match.group("ms"))
                emi_reload_ms.append(milliseconds)
                event_name, value, unit = "emi_reload", milliseconds, "ms"

            if event_name:
                raw_event_count += 1
                clock_events.append((clock_seconds, event_name, {"subject": subject, "value": value, "unit": unit}))

    start_clock: int | None = None
    for clock_seconds, event_name, _data in clock_events:
        if event_name == "modlauncher_start":
            start_clock = clock_seconds
            break
    if start_clock is None and clock_events:
        start_clock = clock_events[0][0]

    events: list[dict[str, Any]] = []
    day_offset = 0
    prior_clock: int | None = None
    first_elapsed: int | None = None
    for clock_seconds, event_name, data in clock_events:
        adjusted = clock_seconds + day_offset
        if prior_clock is not None and adjusted < prior_clock:
            day_offset += 86400
            adjusted = clock_seconds + day_offset
        prior_clock = adjusted
        if first_elapsed is None and event_name == "modlauncher_start":
            first_elapsed = adjusted
        elapsed = adjusted - (first_elapsed if first_elapsed is not None else (start_clock or adjusted))
        events.append(
            {
                "log_clock": f"{clock_seconds // 3600:02}:{(clock_seconds // 60) % 60:02}:{clock_seconds % 60:02}",
                "elapsed_from_modlauncher_s": elapsed,
                "event": event_name,
                **data,
            }
        )

    def first_elapsed_for(name: str) -> int | None:
        return next((row["elapsed_from_modlauncher_s"] for row in events if row["event"] == name), None)

    tick_summary = stats(backlog_ms)
    tick_summary["ticksBehindMean"] = statistics.fmean(backlog_ticks) if backlog_ticks else None
    tick_summary["sampleMeaning"] = "log backlog accumulated since prior warning; not individual MSPT"
    spawn_summary = None
    if spawn_values:
        spawn_summary = {
            "firstPercent": spawn_values[0][1],
            "lastPercent": spawn_values[-1][1],
            "firstClock": f"{spawn_values[0][0] // 3600:02}:{(spawn_values[0][0] // 60) % 60:02}:{spawn_values[0][0] % 60:02}",
            "lastClock": f"{spawn_values[-1][0] // 3600:02}:{(spawn_values[-1][0] // 60) % 60:02}:{spawn_values[-1][0] % 60:02}",
            "sampleCount": len(spawn_values),
            "elapsedBetweenFirstAndLast_s": max(0, spawn_values[-1][0] - spawn_values[0][0]),
        }

    summary = {
        "sourceLog": path.name,
        "runtimeModCount": runtime_mod_count,
        "minecraftStartupTimer_s": startup_seconds,
        "firstMainMenuSignal_s": first_elapsed_for("main_menu_signal"),
        "integratedServerStart_s": first_elapsed_for("integrated_server_start"),
        "worldDoneMarkerSeconds": world_done_seconds,
        "worldDoneMarker_sFromLaunch": first_elapsed_for("world_done_marker"),
        "spawnPreparation": spawn_summary,
        "tickBacklogWarnings_ms": tick_summary,
        "modernFixWatchdogTick_ms": stats(watchdog_ms),
        "longestModDeferredTasks": sorted(deferred, key=lambda item: item["seconds"], reverse=True)[:20],
        "resourceGeneration_ms": resources,
        "shaderSourceLoads": shader_loads,
        "emiReload_ms": stats(emi_reload_ms),
        "embeddiumInternalModificationCount": sum(len(mods) for mods in conflicts.values()),
        "sharedEmbeddiumTargets": [
            {"class": target, "mods": sorted(mods)}
            for target, mods in sorted(conflicts.items())
            if len(mods) > 1
        ],
        "normalizedEventCount": raw_event_count,
        "severityTaggedLineCounts": {severity: severity_counts.get(severity, 0) for severity in ("error", "warn")},
        "topErrorMessages": [
            {"count": count, "message": message}
            for message, count in error_messages.most_common(20)
        ],
    }
    return summary, events


def discover_jfr_tool(run_info: dict[str, Any], explicit: str | None) -> str | None:
    if explicit:
        return explicit
    found = shutil.which("jfr") or shutil.which("jfr.exe")
    if found:
        return found
    executable = run_info.get("capture", {}).get("javaExecutable")
    if executable:
        sibling = Path(executable).with_name("jfr.exe")
        if sibling.exists():
            return str(sibling)
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        for filename in ("jfr.exe", "jfr"):
            candidate = Path(java_home) / "bin" / filename
            if candidate.exists():
                return str(candidate)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data) / "Packages"
        for path in candidate.glob("Microsoft*/LocalCache/Local/runtime/java-runtime-gamma/windows-x64/java-runtime-gamma/bin/jfr.exe"):
            return str(path)
    return None


def parse_jfr(path: Path, tool: str) -> dict[str, Any]:
    selected = ",".join(
        [
            "minecraft.ServerTickTime",
            "minecraft.ChunkGeneration",
            "jdk.ExecutionSample",
            "jdk.GarbageCollection",
            "jdk.GCPhasePause",
            "jdk.GCHeapSummary",
        ]
    )
    completed = subprocess.run(
        [tool, "print", "--json", "--events", selected, str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    data = json.loads(completed.stdout.lstrip("\ufeff"))
    events = data.get("recording", {}).get("events", [])
    tick_ms: list[float] = []
    gc_pause_s: list[float] = []
    gc_phase_s: list[float] = []
    heap_used_bytes: list[float] = []
    chunk_durations_s: list[float] = []
    counts: dict[str, int] = defaultdict(int)
    stack_methods: dict[str, Counter[str]] = defaultdict(Counter)
    stack_sample_counts: Counter[str] = Counter()

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type", "")
        values = event.get("values") or {}
        counts[event_type] += 1
        if event_type == "minecraft.ServerTickTime":
            duration = duration_seconds(values.get("averageTickDuration"))
            if duration is not None and duration > 0:
                tick_ms.append(duration * 1000)
        elif event_type == "jdk.GarbageCollection":
            pause = duration_seconds(values.get("sumOfPauses"))
            if pause is not None:
                gc_pause_s.append(pause)
        elif event_type == "jdk.GCPhasePause":
            pause = duration_seconds(values.get("duration"))
            if pause is not None:
                gc_phase_s.append(pause)
        elif event_type == "jdk.GCHeapSummary":
            used = values.get("heapUsed")
            if isinstance(used, (int, float)):
                heap_used_bytes.append(float(used))
        elif event_type == "minecraft.ChunkGeneration":
            duration = duration_seconds(values.get("duration"))
            if duration is not None:
                chunk_durations_s.append(duration)
        elif event_type == "jdk.ExecutionSample":
            thread = values.get("sampledThread") or values.get("eventThread") or {}
            thread_name = str(thread.get("javaName") or thread.get("osName") or "unknown")
            stack = values.get("stackTrace") or {}
            frames = stack.get("frames") or []
            if frames:
                stack_sample_counts[thread_name] += 1
                for frame in frames:
                    method = frame.get("method") or {}
                    declaring_type = method.get("type") or {}
                    class_name = declaring_type.get("name") or "unknown"
                    method_name = method.get("name") or "unknown"
                    stack_methods[thread_name][f"{class_name}.{method_name}"] += 1

    gc = {
        "garbageCollectionEvents": counts.get("jdk.GarbageCollection", 0),
        "pauseSecondsSumOfPauses": sum(gc_pause_s) if gc_pause_s else None,
        "gcPhasePauseEventCount": counts.get("jdk.GCPhasePause", 0),
        "gcPhasePauseDurations_s": stats(gc_phase_s),
        "heapUsedBytesObservedAfterGc": stats(heap_used_bytes),
    }
    return {
        "sourceJfr": path.name,
        "durationSampledServerTicks_ms": {
            **stats(tick_ms),
            "sampleMeaning": "Minecraft ServerTickTime interval averages; not per-tick raw durations",
        },
        "gc": gc,
        "chunkGeneration": {
            "eventCount": counts.get("minecraft.ChunkGeneration", 0),
            "duration_s": stats(chunk_durations_s),
            "sampleMeaning": "JFR chunk-generation events present in this recording window",
        },
        "executionSamples": {
            thread: {
                "sampleCount": stack_sample_counts[thread],
                "mostFrequentStackFrames": [
                    {"method": method, "frameCount": frame_count}
                    for method, frame_count in stack_methods[thread].most_common(20)
                ],
            }
            for thread in sorted(stack_sample_counts)
        },
        "selectedJfrEventCounts": dict(sorted(counts.items())),
    }


def float_column(row: dict[str, str], *names: str) -> float | None:
    for name in names:
        raw = row.get(name)
        if raw is None:
            continue
        text = raw.strip()
        if not text or text.lower() in {"na", "nan", "n/a", "not available"}:
            continue
        try:
            value = float(text)
        except ValueError:
            continue
        if math.isfinite(value) and value > 0:
            return value
    return None


def low_fps(frame_times_ms: list[float], fraction: float) -> tuple[float | None, int]:
    if not frame_times_ms:
        return None, 0
    count = max(1, math.ceil(len(frame_times_ms) * fraction))
    slowest = sorted(frame_times_ms, reverse=True)[:count]
    mean_frame_time = statistics.fmean(slowest)
    return 1000 / mean_frame_time, count


def analyze_presentmon(path: Path) -> dict[str, Any]:
    app_frame_times: list[float] = []
    display_frame_times: list[float] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            present_ms = float_column(row, "FrameTime", "MsBetweenPresents")
            display_ms = float_column(row, "DisplayedTime", "MsBetweenDisplayChange")
            if present_ms is not None:
                app_frame_times.append(present_ms)
            if display_ms is not None:
                display_frame_times.append(display_ms)

    chosen = display_frame_times if len(display_frame_times) >= 100 else app_frame_times
    source_metric = (
        "DisplayedTime/MsBetweenDisplayChange"
        if chosen is display_frame_times
        else "FrameTime/MsBetweenPresents"
    )
    low_1, low_1_count = low_fps(chosen, 0.01)
    low_01, low_01_count = low_fps(chosen, 0.001)
    frame_stats = stats(chosen)
    mean_ms = frame_stats["mean"]
    metadata_path = path.with_suffix(".json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig")) if metadata_path.exists() else {}
    return {
        "sourceCsv": path.name,
        "scenario": metadata.get("scenario"),
        "contextNote": metadata.get("contextNote"),
        "startedAtLocal": metadata.get("startedAtLocal"),
        "endedAtLocal": metadata.get("endedAtLocal"),
        "frameCount": len(chosen),
        "metricUsed": source_metric,
        "meanFps": 1000 / mean_ms if mean_ms else None,
        "onePercentLowFps": low_1,
        "onePercentSlowFrameCount": low_1_count,
        "zeroPointOnePercentLowFps": low_01,
        "zeroPointOnePercentSlowFrameCount": low_01_count,
        "frametimeMs": frame_stats,
        "appPresentFrameCount": len(app_frame_times),
        "displayChangeFrameCount": len(display_frame_times),
        "lowDefinition": "1000 / mean frametime of the slowest ceil(N * fraction) frames",
    }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        return list(csv.DictReader(stream))


def summarize_system_samples(path: Path) -> dict[str, Any] | None:
    rows = read_csv_rows(path)
    if not rows:
        return None
    game_rows = [row for row in rows if row.get("pid")]

    def values(source: list[dict[str, str]], column: str) -> list[float]:
        return [float(row[column]) for row in source if row.get(column)]

    process_cpu = values(rows, "process_cpu_pct")
    total_cpu = values(rows, "total_cpu_pct")
    working_set = values(game_rows, "working_set_bytes")
    private_bytes = values(game_rows, "private_bytes")
    free_memory = values(rows, "free_physical_bytes")
    game_free_memory = values(game_rows, "free_physical_bytes")
    return {
        "sampleCount": len(rows),
        "gameProcessSampleCount": len(game_rows),
        "processCpuPctOfWholeMachine": stats(process_cpu),
        "systemCpuPct": stats(total_cpu),
        "systemCpuPctWhileGameRunning": stats(values(game_rows, "total_cpu_pct")),
        "workingSetBytes": stats([float(value) for value in working_set]),
        "privateBytes": stats([float(value) for value in private_bytes]),
        "freePhysicalBytes": stats([float(value) for value in free_memory]),
        "freePhysicalBytesWhileGameRunning": stats(game_free_memory),
        "note": "Working set/private bytes are process memory, not Java heap. Heap comes from JFR or Spark.",
    }


def summarize_pressure_samples(path: Path) -> dict[str, Any] | None:
    rows = read_csv_rows(path)
    if not rows:
        return None

    def floats(column: str) -> list[float]:
        return [float(row[column]) for row in rows if row.get(column)]

    return {
        "sampleCount": len(rows),
        "availableMemoryMiB": stats(floats("available_mib")),
        "committedBytesPct": stats(floats("commit_pct")),
        "pagesPerSecond": stats(floats("pages_per_sec")),
        "pageReadsPerSecond": stats(floats("page_reads_per_sec")),
        "pagesInputPerSecond": stats(floats("pages_input_per_sec")),
        "pagesOutputPerSecond": stats(floats("pages_output_per_sec")),
        "processPageFaultsPerSecond": stats(floats("process_page_faults_per_sec")),
        "processCpuPct": stats(floats("process_cpu_pct")),
        "note": "Windows memory-manager rates are physical paging counters; non-zero rates can also include file-backed page loads.",
    }


def render_markdown(summary: dict[str, Any]) -> str:
    def show(value: Any, digits: int = 2) -> str:
        if value is None:
            return "n/d"
        if isinstance(value, float):
            return f"{value:.{digits}f}"
        return str(value)

    lines = [
        f"# Performance capture: {summary.get('runId', 'unlabeled')}",
        "",
        f"- Scenario: `{summary.get('scenario', 'unknown')}`",
        f"- Commit: `{summary.get('git', {}).get('commit', 'unknown')}`",
        f"- Status: `{summary.get('status', 'unknown')}`",
        "",
        "## Startup and world loading",
        "",
    ]
    log = summary.get("log", {})
    lines.extend(
        [
            f"- Loaded runtime mods: {show(log.get('runtimeModCount'), 0)}",
            f"- Minecraft startup timer: {show(log.get('minecraftStartupTimer_s'))} s",
            f"- First main menu signal: {show(log.get('firstMainMenuSignal_s'))} s from launch",
            f"- Human menu-ready mark: {show(next((item.get('elapsed_s') for item in summary.get('phaseEvents', []) if item.get('event') == 'menu-ready'), None))} s from capture start",
            f"- Integrated server start: {show(log.get('integratedServerStart_s'))} s from launch",
            f"- World `Done` marker: {show(log.get('worldDoneMarker_sFromLaunch'))} s from launch",
            f"- Human world-ready mark: {show(next((item.get('elapsed_s') for item in summary.get('phaseEvents', []) if item.get('event') == 'world-ready'), None))} s from capture start",
            f"- Spawn progress: {show((log.get('spawnPreparation') or {}).get('firstPercent'), 0)}% to {show((log.get('spawnPreparation') or {}).get('lastPercent'), 0)}% in {show((log.get('spawnPreparation') or {}).get('elapsedBetweenFirstAndLast_s'), 0)} s",
            "",
        ]
    )
    error_lines = (log.get("severityTaggedLineCounts") or {}).get("error", 0)
    warn_lines = (log.get("severityTaggedLineCounts") or {}).get("warn", 0)
    if error_lines:
        lines.extend(["", "## Startup log errors", "", f"- Severity-tagged messages: {error_lines} ERROR, {warn_lines} WARN."])
        for item in (log.get("topErrorMessages") or [])[:8]:
            lines.append(f"- `{item['count']}×` {item['message']}")
    lines.extend(["", "## CPU and memory", ""])
    system = summary.get("systemSamples") or {}
    process_cpu = system.get("processCpuPctOfWholeMachine") or {}
    total_cpu = system.get("systemCpuPct") or {}
    game_cpu = system.get("systemCpuPctWhileGameRunning") or {}
    working_set = system.get("workingSetBytes") or {}
    free_memory = system.get("freePhysicalBytesWhileGameRunning") or system.get("freePhysicalBytes") or {}
    pressure = summary.get("systemPressureSamples") or {}
    available_pressure = pressure.get("availableMemoryMiB") or {}
    commit_pressure = pressure.get("committedBytesPct") or {}
    page_reads = pressure.get("pageReadsPerSecond") or {}
    if system:
        lines.append(
            f"- Java process CPU mean/p95/max: {show(process_cpu.get('mean'))}/{show(process_cpu.get('p95'))}/{show(process_cpu.get('max'))}% of total logical CPU; system CPU while Java ran mean/p95/max: {show(game_cpu.get('mean'))}/{show(game_cpu.get('p95'))}/{show(game_cpu.get('max'))}% (whole capture: {show(total_cpu.get('mean'))}% mean)."
        )
        lines.append(
            f"- Java working-set p95/max: {show((working_set.get('p95') or 0) / (1024 * 1024))}/{show((working_set.get('max') or 0) / (1024 * 1024))} MiB; free physical RAM median/min: {show((free_memory.get('p50') or 0) / (1024 * 1024))}/{show((free_memory.get('min') or 0) / (1024 * 1024))} MiB."
        )
    if pressure:
        lines.append(
            f"- Short pressure sample n={pressure.get('sampleCount')}: committed memory mean/max {show(commit_pressure.get('mean'))}/{show(commit_pressure.get('max'))}%; available RAM mean/min {show(available_pressure.get('mean'))}/{show(available_pressure.get('min'))} MiB; page reads/sec p95/max {show(page_reads.get('p95'), 0)}/{show(page_reads.get('max'), 0)}."
        )
    if not system and not pressure:
        lines.append("- No CPU or memory time series found.")
    lines.extend(["", "## Frametime", ""])
    frames = summary.get("presentMon", [])
    if frames:
        for capture in frames:
            if capture["frameCount"]:
                lines.append(
                    f"- `{capture['sourceCsv']}` ({capture['scenario'] or 'scenario unspecified'}, {capture['frameCount']} frames, {capture['metricUsed']}): mean {show(capture['meanFps'])} FPS; 1% low {show(capture['onePercentLowFps'])}; 0.1% low {show(capture['zeroPointOnePercentLowFps'])}; frametime p95/p99 {show(capture['frametimeMs'].get('p95'))}/{show(capture['frametimeMs'].get('p99'))} ms. Context: {(capture['contextNote'] or 'none').rstrip('.')}."
                )
            else:
                lines.append(f"- `{capture['sourceCsv']}` returned no usable frames; do not treat it as an FPS sample. Context: {capture['contextNote'] or 'none'}.")
    else:
        lines.append("- No PresentMon frame CSV found.")
    lines.extend(["", "## Tick backlog and JFR", ""])
    backlog = log.get("tickBacklogWarnings_ms", {})
    lines.append(
        f"- Log backlog warnings: {show(backlog.get('count'), 0)}; mean/p95/p99/max {show(backlog.get('mean'))}/{show(backlog.get('p95'))}/{show(backlog.get('p99'))}/{show(backlog.get('max'))} ms. These are accumulated delays between warnings, not individual MSPT."
    )
    spark_rows = summary.get("sparkSamples") or []
    if spark_rows:
        sample = spark_rows[-1]
        lines.append(
            f"- Latest Spark sample ({sample.get('timestamp_utc', 'time unknown')}): measured rolling TPS {show(sample.get('mean_tps'))}; mean/p50/p95/p99/max MSPT {show(sample.get('average_mspt'))}/{show(sample.get('p50_mspt'))}/{show(sample.get('p95_mspt'))}/{show(sample.get('p99_mspt'))}/{show(sample.get('max_mspt'))}."
        )
    tick_rows = summary.get("tickSamples") or []
    if tick_rows:
        sample = tick_rows[-1]
        lines.append(
            f"- Latest Boundless Tweaks sample ({sample.get('timestamp_utc', 'time unknown')}): mean-tick-time TPS equivalent {show(sample.get('mean_tps'))}; mean/p50/p95/p99/max MSPT {show(sample.get('average_mspt'))}/{show(sample.get('p50_mspt'))}/{show(sample.get('p95_mspt'))}/{show(sample.get('p99_mspt'))}/{show(sample.get('max_mspt'))}."
        )
    jfr = summary.get("jfr")
    if jfr:
        ticks = jfr["durationSampledServerTicks_ms"]
        gc = jfr["gc"]
        chunks = jfr["chunkGeneration"]
        lines.extend(
            [
                f"- JFR ServerTickTime window averages: n={ticks['count']}, mean/p95/p99/max {show(ticks['mean'])}/{show(ticks['p95'])}/{show(ticks['p99'])}/{show(ticks['max'])} ms.",
                f"- GC pause sum from GarbageCollection events: {show(gc.get('pauseSecondsSumOfPauses'))} s; GC event count {show(gc.get('garbageCollectionEvents'), 0)}.",
                f"- JFR chunk-generation events: {show(chunks.get('eventCount'), 0)}.",
            ]
        )
        for thread, samples in jfr.get("executionSamples", {}).items():
            frequent = ", ".join(item["method"] for item in samples.get("mostFrequentStackFrames", [])[:5])
            lines.append(f"- JFR execution samples for thread `{thread}`: n={samples['sampleCount']}; most frequent stack frames: {frequent or 'none'}.")
    else:
        lines.append("- No JFR recording found or the local `jfr` tool was unavailable.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--log", type=Path, help="Override the copied latest.log")
    parser.add_argument("--jfr-tool", help="Path to the JDK jfr executable")
    args = parser.parse_args()

    run_directory = args.run_directory.resolve()
    run_info_path = run_directory / "run.json"
    run_info = json.loads(run_info_path.read_text(encoding="utf-8-sig")) if run_info_path.exists() else {}
    summary: dict[str, Any] = {
        "runId": run_info.get("runId", run_directory.name),
        "scenario": run_info.get("scenario"),
        "status": run_info.get("status"),
        "git": run_info.get("git", {}),
        "runtime": run_info.get("minecraft", {}),
        "world": run_info.get("world", {}),
        "visual": run_info.get("visual", {}),
        "inventory": run_info.get("inventory", {}),
    }

    log_path = args.log.resolve() if args.log else run_directory / "latest.log"
    if log_path.exists():
        log_summary, events = parse_log(log_path)
        summary["log"] = log_summary
        write_csv(
            run_directory / "log-events.csv",
            events,
            ["log_clock", "elapsed_from_modlauncher_s", "event", "subject", "value", "unit"],
        )

    system_summary = summarize_system_samples(run_directory / "system-samples.csv")
    if system_summary:
        summary["systemSamples"] = system_summary

    pressure_summary = summarize_pressure_samples(run_directory / "system-pressure-samples.csv")
    if pressure_summary:
        summary["systemPressureSamples"] = pressure_summary

    jfr_files = sorted(run_directory.glob("*.jfr"))
    jfr_tool = discover_jfr_tool(run_info, args.jfr_tool)
    if jfr_files and jfr_tool:
        summary["jfr"] = parse_jfr(jfr_files[-1], jfr_tool)

    frametime_files = sorted(run_directory.glob("frametime-*.csv"))
    if frametime_files:
        summary["presentMon"] = [analyze_presentmon(path) for path in frametime_files]

    spark_samples = read_csv_rows(run_directory / "spark-samples.csv")
    if spark_samples:
        summary["sparkSamples"] = spark_samples
    tick_samples = read_csv_rows(run_directory / "tick-samples.csv")
    if tick_samples:
        summary["tickSamples"] = tick_samples
    manual_samples = read_csv_rows(run_directory / "manual-f3.csv")
    if manual_samples:
        summary["manualF3Samples"] = manual_samples
    event_rows = read_csv_rows(run_directory / "events.csv")
    if event_rows:
        summary["phaseEvents"] = [
            {
                "timestamp_utc": row.get("timestamp_utc", ""),
                "event": row.get("event", ""),
                "scenario": row.get("scenario", ""),
                "elapsed_s": float(row["elapsed_s"]) if row.get("elapsed_s") else None,
                "note": row.get("note", ""),
            }
            for row in event_rows
        ]

    (run_directory / "analysis.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_directory / "analysis.md").write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
