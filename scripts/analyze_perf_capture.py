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
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
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


def iter_jfr_json_events(stream: Any):
    """Yield JFR JSON events incrementally without materializing the recording."""
    decoder = json.JSONDecoder()
    marker = '"events"'
    buffer = ""
    eof = False

    while marker not in buffer:
        chunk = stream.read(64 * 1024)
        if not chunk:
            raise ValueError("JFR JSON output does not contain a recording.events array")
        buffer += chunk

    marker_end = buffer.index(marker) + len(marker)
    buffer = buffer[marker_end:]

    while True:
        while True:
            buffer = buffer.lstrip()
            if buffer.startswith(":"):
                buffer = buffer[1:]
            elif buffer.startswith("["):
                buffer = buffer[1:]
                break
            elif not eof:
                chunk = stream.read(64 * 1024)
                if chunk:
                    buffer += chunk
                else:
                    eof = True
            else:
                raise ValueError("JFR JSON events key is not followed by an array")

        while True:
            buffer = buffer.lstrip()
            if buffer.startswith(","):
                buffer = buffer[1:]
                continue
            if buffer.startswith("]"):
                return
            if not buffer:
                if eof:
                    raise ValueError("Unexpected end of JFR JSON events array")
                chunk = stream.read(64 * 1024)
                if chunk:
                    buffer += chunk
                else:
                    eof = True
                continue

            try:
                event, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError as exc:
                if eof:
                    raise ValueError("Incomplete JFR JSON event") from exc
                chunk = stream.read(64 * 1024)
                if chunk:
                    buffer += chunk
                    if len(buffer) > 8 * 1024 * 1024:
                        raise ValueError("JFR JSON event exceeded the 8 MiB streaming buffer") from exc
                else:
                    eof = True
                continue

            buffer = buffer[end:]
            yield event


def read_jfr_events(path: Path, tool: str, selected: str):
    """Run the JFR CLI into a temporary file and stream its event array."""
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as output:
        subprocess.run(
            [tool, "print", "--json", "--events", selected, str(path)],
            stdout=output,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        output.seek(0)
        yield from iter_jfr_json_events(output)


class JfrAllocationMetrics:
    """Summarize allocation samples and per-thread allocation-counter deltas."""

    def __init__(self) -> None:
        self.object_sample_count = 0
        self.object_classes: Counter[str] = Counter()
        self.allocation_sites: Counter[str] = Counter()
        self.thread_counters: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _frame_name(frame: dict[str, Any]) -> str:
        method = frame.get("method") or {}
        declaring_type = method.get("type") or {}
        class_name = declaring_type.get("name") or "unknown"
        method_name = method.get("name") or "unknown"
        return f"{class_name}.{method_name}"

    def add(self, event_type: str, values: dict[str, Any], event_time: datetime | None) -> None:
        if event_type == "jdk.ObjectAllocationSample":
            self.object_sample_count += 1
            object_class = values.get("objectClass") or {}
            class_name = object_class.get("name") if isinstance(object_class, dict) else str(object_class)
            self.object_classes[class_name or "unknown"] += 1

            frames = (values.get("stackTrace") or {}).get("frames") or []
            for frame in frames:
                site = self._frame_name(frame)
                if not site.startswith((
                    "java/", "jdk/", "sun/", "org/spongepowered/asm/", "net/minecraftforge/"
                )):
                    self.allocation_sites[site] += 1
                    break
            return

        if event_type != "jdk.ThreadAllocationStatistics" or event_time is None:
            return

        allocated = values.get("allocated")
        thread = values.get("thread") or {}
        if not isinstance(allocated, (int, float)) or not isinstance(thread, dict):
            return
        thread_id = thread.get("javaThreadId")
        if thread_id is None:
            thread_id = thread.get("osThreadId")
        if thread_id is None:
            thread_id = thread.get("javaName") or thread.get("osName") or "unknown"
        key = str(thread_id)
        name = str(thread.get("javaName") or thread.get("osName") or "unknown")
        snapshot = self.thread_counters.get(key)
        current = {"time": event_time, "allocated": int(allocated), "name": name}
        if snapshot is None:
            self.thread_counters[key] = {"first": current, "last": current}
        else:
            if event_time < snapshot["first"]["time"]:
                snapshot["first"] = current
            if event_time > snapshot["last"]["time"]:
                snapshot["last"] = current

    def summary(self) -> dict[str, Any]:
        thread_deltas: list[dict[str, Any]] = []
        for snapshot in self.thread_counters.values():
            first = snapshot["first"]
            last = snapshot["last"]
            elapsed = (last["time"] - first["time"]).total_seconds()
            delta = last["allocated"] - first["allocated"]
            if elapsed <= 0 or delta < 0:
                continue
            thread_deltas.append({
                "thread": last["name"],
                "allocatedBytes": delta,
                "observedSeconds": elapsed,
                "allocatedMiBPerSecond": delta / elapsed / (1024 * 1024),
            })

        if thread_deltas:
            sampled_intervals = [
                snapshot
                for snapshot in self.thread_counters.values()
                if snapshot["last"]["time"] > snapshot["first"]["time"]
            ]
            reference_start = min(snapshot["first"]["time"] for snapshot in sampled_intervals)
            reference_end = max(snapshot["last"]["time"] for snapshot in sampled_intervals)
            reference_seconds = max(0.0, (reference_end - reference_start).total_seconds())
            observed_bytes = sum(item["allocatedBytes"] for item in thread_deltas)
        else:
            reference_seconds = 0.0
            observed_bytes = 0

        return {
            "objectAllocationSampleCount": self.object_sample_count,
            "mostSampledObjectClasses": [
                {"class": name, "sampleCount": count}
                for name, count in self.object_classes.most_common(20)
            ],
            "mostSampledAllocationSites": [
                {"site": site, "sampleCount": count}
                for site, count in self.allocation_sites.most_common(20)
            ],
            "threadAllocationCounters": {
                "threadIntervalCount": len(thread_deltas),
                "observedIntervalSeconds": reference_seconds,
                "observedAllocatedBytes": observed_bytes,
                "observedAllocatedMiBPerSecond": (
                    observed_bytes / reference_seconds / (1024 * 1024) if reference_seconds else None
                ),
                "mostAllocatedThreads": sorted(
                    thread_deltas,
                    key=lambda item: item["allocatedBytes"],
                    reverse=True,
                )[:20],
                "sampleMeaning": (
                    "Per-thread cumulative allocation-counter differences between the first and last "
                    "JFR ThreadAllocationStatistics events in the selected window. Object allocation "
                    "classes and sites are sampled counts, not exact object counts."
                ),
            },
        }


def parse_jfr(
    path: Path,
    tool: str,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> dict[str, Any]:
    selected = ",".join(
        [
            "minecraft.ServerTickTime",
            "minecraft.ChunkGeneration",
            "jdk.ExecutionSample",
            "jdk.GarbageCollection",
            "jdk.GCPhasePause",
            "jdk.GCHeapSummary",
            "jdk.ObjectAllocationSample",
            "jdk.ThreadAllocationStatistics",
        ]
    )
    events = read_jfr_events(path, tool, selected)
    tick_ms: list[float] = []
    gc_pause_s: list[float] = []
    gc_phase_s: list[float] = []
    heap_used_after_gc_bytes: list[float] = []
    heap_used_before_gc_bytes: list[float] = []
    heap_summary_when_counts: Counter[str] = Counter()
    chunk_durations_s: list[float] = []
    counts: dict[str, int] = defaultdict(int)
    stack_methods: dict[str, Counter[str]] = defaultdict(Counter)
    stack_sample_counts: Counter[str] = Counter()
    allocation_metrics = JfrAllocationMetrics()

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type", "")
        values = event.get("values") or {}
        event_time = parse_iso_datetime(values.get("startTime") or event.get("startTime"))
        if window_start is not None and (event_time is None or event_time < window_start):
            continue
        if window_end is not None and (event_time is None or event_time > window_end):
            continue
        counts[event_type] += 1
        if event_type in ("jdk.ObjectAllocationSample", "jdk.ThreadAllocationStatistics"):
            allocation_metrics.add(event_type, values, event_time)
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
                when = str(values.get("when") or "unknown").strip().lower()
                heap_summary_when_counts[when] += 1
                if when == "after gc":
                    heap_used_after_gc_bytes.append(float(used))
                elif when == "before gc":
                    heap_used_before_gc_bytes.append(float(used))
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
        "heapUsedBytesObservedAfterGc": stats(heap_used_after_gc_bytes),
        "heapUsedBytesObservedBeforeGc": stats(heap_used_before_gc_bytes),
        "heapSummaryWhenCounts": dict(sorted(heap_summary_when_counts.items())),
    }
    return {
        "sourceJfr": path.name,
        "windowUtc": {
            "start": window_start.isoformat() if window_start else None,
            "end": window_end.isoformat() if window_end else None,
        },
        "durationSampledServerTicks_ms": {
            **stats(tick_ms),
            "above50msCount": sum(1 for value in tick_ms if value > 50),
            "above50msPercentOfSamples": (100 * sum(1 for value in tick_ms if value > 50) / len(tick_ms)) if tick_ms else None,
            "sampleMeaning": "Minecraft ServerTickTime interval averages; not per-tick raw durations",
        },
        "gc": gc,
        "chunkGeneration": {
            "eventCount": counts.get("minecraft.ChunkGeneration", 0),
            "duration_s": stats(chunk_durations_s),
            "sampleMeaning": "JFR chunk-generation events present in this recording window",
        },
        "allocationDiagnostics": allocation_metrics.summary(),
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
    casefolded = {key.casefold(): value for key, value in row.items() if key}
    for name in names:
        raw = row.get(name)
        if raw is None:
            raw = casefolded.get(name.casefold())
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
    max_frame_ms = frame_stats["max"]
    freeze_thresholds = (50, 100, 250, 500, 1000)
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
        "minimumObservedFps": 1000 / max_frame_ms if max_frame_ms else None,
        "maximumFrameFreezeMs": max_frame_ms,
        "framesOverThresholdMs": {
            str(threshold): sum(1 for value in chosen if value > threshold)
            for threshold in freeze_thresholds
        },
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


def summarize_system_samples(path: Path, rows: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    rows = read_csv_rows(path) if rows is None else rows
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


def summarize_pressure_from_system_samples(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    if not rows:
        return None

    def floats(column: str, scale: float = 1.0) -> list[float]:
        return [float(row[column]) / scale for row in rows if row.get(column)]

    return {
        "sampleCount": len(rows),
        "availableMemoryMiB": stats(floats("free_physical_bytes", 1024 * 1024)),
        "committedBytesPct": stats(floats("commit_pct")),
        "pagesPerSecond": stats(floats("pages_per_sec")),
        "pageReadsPerSecond": stats(floats("page_reads_per_sec")),
        "pagesInputPerSecond": stats(floats("pages_input_per_sec")),
        "pagesOutputPerSecond": stats(floats("pages_output_per_sec")),
        "processPageFaultsPerSecond": stats(floats("process_page_faults_per_sec")),
        "processCpuPct": stats(floats("process_cpu_pct")),
        "note": "Windows memory-manager rates are physical paging counters; non-zero rates can also include file-backed page loads.",
    }


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
                    f"- `{capture['sourceCsv']}` ({capture['scenario'] or 'scenario unspecified'}, {capture['frameCount']} frames, {capture['metricUsed']}): mean/min observed {show(capture['meanFps'])}/{show(capture.get('minimumObservedFps'))} FPS; 1% low {show(capture['onePercentLowFps'])}; 0.1% low {show(capture['zeroPointOnePercentLowFps'])}; frametime mean/p50/p95/p99/max {show(capture['frametimeMs'].get('mean'))}/{show(capture['frametimeMs'].get('p50'))}/{show(capture['frametimeMs'].get('p95'))}/{show(capture['frametimeMs'].get('p99'))}/{show(capture['maximumFrameFreezeMs'])} ms; >50/>100/>250/>500/>1000 ms frames {capture.get('framesOverThresholdMs', {}).get('50', 0)}/{capture.get('framesOverThresholdMs', {}).get('100', 0)}/{capture.get('framesOverThresholdMs', {}).get('250', 0)}/{capture.get('framesOverThresholdMs', {}).get('500', 0)}/{capture.get('framesOverThresholdMs', {}).get('1000', 0)}. Context: {(capture['contextNote'] or 'none').rstrip('.')}."
                )
            else:
                lines.append(f"- `{capture['sourceCsv']}` returned no usable frames; do not treat it as an FPS sample. Context: {capture['contextNote'] or 'none'}.")
    else:
        lines.append("- No PresentMon frame CSV found.")
    window_samples = summary.get("presentMonWindowSamples") or {}
    if window_samples:
        lines.extend(["", "## Host metrics aligned to PresentMon windows", ""])
        for capture in frames:
            window = window_samples.get(capture.get("sourceCsv"))
            if not window:
                continue
            aligned_system = window.get("systemSamples") or {}
            aligned_pressure = window.get("systemPressureSamples") or {}
            cpu = aligned_system.get("processCpuPctOfWholeMachine") or {}
            system_cpu = aligned_system.get("systemCpuPctWhileGameRunning") or {}
            working_set = aligned_system.get("workingSetBytes") or {}
            private = aligned_system.get("privateBytes") or {}
            free = aligned_system.get("freePhysicalBytesWhileGameRunning") or {}
            available = aligned_pressure.get("availableMemoryMiB") or {}
            commit = aligned_pressure.get("committedBytesPct") or {}
            page_reads = aligned_pressure.get("pageReadsPerSecond") or {}
            pages = aligned_pressure.get("pagesPerSecond") or {}
            lines.append(
                f"- `{capture.get('sourceCsv')}`: {aligned_system.get('sampleCount', 0)} system samples; Java CPU mean/p95/max {show(cpu.get('mean'))}/{show(cpu.get('p95'))}/{show(cpu.get('max'))}% of whole machine; system CPU p95/max {show(system_cpu.get('p95'))}/{show(system_cpu.get('max'))}%; working set p95/max {show((working_set.get('p95') or 0) / (1024 * 1024))}/{show((working_set.get('max') or 0) / (1024 * 1024))} MiB; private bytes p95/max {show((private.get('p95') or 0) / (1024 * 1024))}/{show((private.get('max') or 0) / (1024 * 1024))} MiB."
            )
            lines.append(
                f"  Physical memory median/min {show((free.get('p50') or 0) / (1024 * 1024))}/{show((free.get('min') or 0) / (1024 * 1024))} MiB (available-memory equivalent {show(available.get('mean'))}/{show(available.get('min'))} MiB mean/min); commit mean/max {show(commit.get('mean'))}/{show(commit.get('max'))}%; pages/sec p95/max {show(pages.get('p95'), 0)}/{show(pages.get('max'), 0)}; page reads/sec p95/max {show(page_reads.get('p95'), 0)}/{show(page_reads.get('max'), 0)}."
            )
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
        allocations = jfr.get("allocationDiagnostics") or {}
        thread_allocations = allocations.get("threadAllocationCounters") or {}
        if allocations.get("objectAllocationSampleCount") or thread_allocations.get("threadIntervalCount"):
            top_classes = ", ".join(
                f"{item['class']} ({item['sampleCount']})"
                for item in allocations.get("mostSampledObjectClasses", [])[:5]
            )
            top_sites = ", ".join(
                f"{item['site']} ({item['sampleCount']})"
                for item in allocations.get("mostSampledAllocationSites", [])[:5]
            )
            thread_names = ", ".join(
                f"{item['thread']} {show(item['allocatedBytes'] / (1024 * 1024))} MiB"
                for item in thread_allocations.get("mostAllocatedThreads", [])[:5]
            )
            lines.append(
                f"- JFR thread allocation counters: {show(thread_allocations.get('observedAllocatedMiBPerSecond'))} MiB/s aggregate over {show(thread_allocations.get('observedIntervalSeconds'))} s; highest threads: {thread_names or 'none'}."
            )
            lines.append(
                f"  Sampled object classes: {top_classes or 'none'}; sampled allocation sites: {top_sites or 'none'}. Counts are JFR samples, not exact object counts."
            )
        for capture_name, capture_jfr in (summary.get("jfrByPresentMonWindow") or {}).items():
            window_ticks = capture_jfr["durationSampledServerTicks_ms"]
            window_gc = capture_jfr["gc"]
            over_budget = window_ticks.get("count", 0)
            above_50 = window_ticks.get("above50msCount", 0)
            lines.append(
                f"- JFR aligned to `{capture_name}`: {window_ticks['count']} sampled ServerTickTime averages; mean/p95/p99/max {show(window_ticks.get('mean'))}/{show(window_ticks.get('p95'))}/{show(window_ticks.get('p99'))}/{show(window_ticks.get('max'))} ms; {above_50}/{over_budget} sampled intervals above 50 ms. These are rolling/interval averages, not individual tick durations."
            )
            phase = window_gc.get("gcPhasePauseDurations_s") or {}
            lines.append(
                f"  GC pauses in window: {window_gc.get('gcPhasePauseEventCount', 0)} GC phase events, p95/max {show((phase.get('p95') or 0) * 1000)}/{show((phase.get('max') or 0) * 1000)} ms; total collection pauses {show(window_gc.get('pauseSecondsSumOfPauses'))} s."
            )
            for thread in ("Server thread", "Render thread", "Chunk Render Task Executor #0"):
                samples = capture_jfr.get("executionSamples", {}).get(thread)
                if samples:
                    frequent = ", ".join(item["method"] for item in samples.get("mostFrequentStackFrames", [])[:5])
                    lines.append(f"  `{thread}` samples n={samples['sampleCount']}: {frequent or 'none'}. ")
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

    system_sample_path = run_directory / "system-samples.csv"
    system_rows = read_csv_rows(system_sample_path)
    system_summary = summarize_system_samples(system_sample_path, system_rows)
    if system_summary:
        summary["systemSamples"] = system_summary

    pressure_summary = summarize_pressure_samples(run_directory / "system-pressure-samples.csv")
    if not pressure_summary:
        pressure_summary = summarize_pressure_from_system_samples(system_rows)
    if pressure_summary:
        summary["systemPressureSamples"] = pressure_summary

    jfr_files = sorted(run_directory.glob("*.jfr"), key=lambda item: item.stat().st_mtime)
    jfr_tool = discover_jfr_tool(run_info, args.jfr_tool)
    if jfr_files and jfr_tool:
        summary["jfr"] = parse_jfr(jfr_files[-1], jfr_tool)

    frametime_files = sorted(run_directory.glob("frametime-*.csv"))
    if frametime_files:
        summary["presentMon"] = [analyze_presentmon(path) for path in frametime_files]
        window_samples: dict[str, Any] = {}
        jfr_window_summaries: dict[str, Any] = {}
        for capture in summary["presentMon"]:
            start = parse_iso_datetime(capture.get("startedAtLocal"))
            end = parse_iso_datetime(capture.get("endedAtLocal"))
            if start is None or end is None:
                continue
            selected_rows = []
            for row in system_rows:
                sample_time = parse_iso_datetime(row.get("timestamp_utc"))
                if sample_time is not None and start <= sample_time <= end:
                    selected_rows.append(row)
            window_samples[capture["sourceCsv"]] = {
                "startedAtLocal": capture.get("startedAtLocal"),
                "endedAtLocal": capture.get("endedAtLocal"),
                "systemSamples": summarize_system_samples(system_sample_path, selected_rows),
                "systemPressureSamples": summarize_pressure_from_system_samples(selected_rows),
            }
            if jfr_files and jfr_tool:
                jfr_window_summaries[capture["sourceCsv"]] = parse_jfr(
                    jfr_files[-1], jfr_tool, start, end
                )
        summary["presentMonWindowSamples"] = window_samples
        if jfr_window_summaries:
            summary["jfrByPresentMonWindow"] = jfr_window_summaries

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
