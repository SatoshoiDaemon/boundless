#!/usr/bin/env python3
"""Sample Java RSS/CPU and runner memory while the client is running."""

from __future__ import annotations

import argparse
import csv
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path


STOP = False


def stop(_signum: int, _frame: object) -> None:
    global STOP
    STOP = True


def memory_available_mb() -> float:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024.0
    return float("nan")


def java_processes() -> list[tuple[int, int, int, str]]:
    processes: list[tuple[int, int, int, str]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8").strip()
            if comm not in {"java", "javaw"}:
                continue
            status = (entry / "status").read_text(encoding="utf-8")
            rss_kb = next(int(line.split()[1]) for line in status.splitlines() if line.startswith("VmRSS:"))
            stat = (entry / "stat").read_text(encoding="utf-8")
            fields = stat[stat.rfind(")") + 2 :].split()
            cpu_ticks = int(fields[11]) + int(fields[12])
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
            if "headlessmc" in command.lower() or "minecraft" in command.lower() or "bootstraplauncher" in command.lower():
                processes.append((int(entry.name), rss_kb, cpu_ticks, command[:240]))
        except (FileNotFoundError, PermissionError, StopIteration, ValueError, IndexError):
            continue
    return processes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stop-file", required=True, type=Path)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    previous_cpu: dict[int, tuple[int, float]] = {}
    clock_ticks = os.sysconf("SC_CLK_TCK")
    with args.output.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target)
        writer.writerow(("timestamp_utc", "java_process_count", "java_rss_mb", "max_java_rss_mb",
                         "host_mem_available_mb", "max_java_cpu_pct_one_core", "java_pids"))
        while not STOP and not args.stop_file.exists():
            now = time.monotonic()
            processes = java_processes()
            cpu_rates: list[float] = []
            for pid, _rss, cpu_ticks, _command in processes:
                prior = previous_cpu.get(pid)
                if prior is not None:
                    old_ticks, old_time = prior
                    elapsed = now - old_time
                    if elapsed > 0:
                        cpu_rates.append(max(0.0, (cpu_ticks - old_ticks) / clock_ticks / elapsed * 100.0))
                previous_cpu[pid] = (cpu_ticks, now)
            rss_values = [rss for _pid, rss, _cpu, _command in processes]
            writer.writerow((datetime.now(timezone.utc).isoformat(), len(processes),
                             round(sum(rss_values) / 1024.0, 2),
                             round(max(rss_values, default=0) / 1024.0, 2),
                             round(memory_available_mb(), 2), round(max(cpu_rates, default=0.0), 2),
                             ";".join(str(pid) for pid, _rss, _cpu, _command in processes)))
            target.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
