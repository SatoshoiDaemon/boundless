# Boundless P0.1 benchmark protocol

This protocol records a repeatable run before any performance changes. A run directory locks the Git revision, every direct `mods/*.jar` SHA-256, all configuration files under `config/`, `options.txt`, the selected shaderpack, hardware, Java/Forge version, scenario, seed, route, and visual profile. Raw run directories are ignored by Git; reviewed summaries and comparison tables are versioned.

## Scenarios

Run each scenario at least three times against the same committed pack state. Keep the player route, camera, time/weather, resolution, render/simulation distance, shader profile, and background workload fixed. Record seed and coordinates. For A/B changes, change one mod or setting per comparison and preserve the baseline run directory.

1. **Client startup:** start capture before clicking Play. Mark `menu-ready` when the main-menu buttons become usable. Keep a separate 120-second menu frame capture after the menu is stable. Startup duration is measured from the ModLauncher timestamp and cross-checked with `Game took ... seconds to start`; the menu mark is the exact human-visible endpoint.
2. **Existing-world entry:** mark `menu-ready`, load the named save, then mark `world-ready` only after the player can move and the spawn area has settled. Record the elapsed interval and the same save/seed for every repetition.
3. **Stationary loaded chunks:** use a fixed saved location and camera direction. Wait 120 seconds after world entry, then capture 180 seconds without movement. Record Spark and `/boundless perf` once at the start and end.
4. **Pregenerated exploration:** make a disposable copy of the same world after preparing a fixed route. Repeat the same waypoints, vehicle/speed, camera, and duration. Record the route coordinates and keep the save copy unchanged between repetitions.
5. **New terrain:** start each repetition from a fresh copy of the same seed and base save. Choose a route that has not been visited or generated; do not pre-teleport across the target region. Record route coordinates and confirm the region files were absent before the run. Capture at least 300 seconds.

Do not compare a cold first launch with a warmed launch as if they were identical. Keep both and label them. Do not clear caches or change system settings between repetitions. Note Windows updates, other foreground applications, battery/power state, thermal throttling, and any background workload.

## Starting a capture

From the repository root in PowerShell:

```powershell
.\scripts\capture_perf_session.ps1 `
  -Scenario client-startup `
  -RunId baseline-startup-r1 `
  -WorldLabel "Boundless test save" `
  -Seed "paste seed here" `
  -Route "menu only" `
  -VisualProfile "Complementary Reimagined + Euphoria; Custom Popular; Fancy; RD12; SD8; 1920x1080"
```

Allowed `-Scenario` values are `client-startup`, `existing-world-entry`, `stationary-loaded-chunks`, `exploration-generated`, and `exploration-new-terrain`. At the prompt, launch the instance from CurseForge. Press Enter in the capture window to close the run after the last scenario. The script samples Java process/system CPU and memory every two seconds, saves the active log, and optionally attaches JFR. Use `-ProfileJfr -JfrDurationMinutes 45` on a separate diagnostic run when profiling overhead should be kept out of the main timing run.

The run path is printed at start and is `auditoria/testes/runs/<date>/<RunId>`. The `run.json` `git.workingTreeClean` value must be `true` for a clean baseline. If it is false, commit the tested state or preserve the JAR/config lock hashes with the run.

## Marking phases and collecting FPS

Mark exact menu/world/scenario endpoints from a second PowerShell window. Example:

```powershell
$run = "auditoria/testes/runs/2026-11-13/baseline-startup-r1"
.\scripts\mark_perf_event.ps1 -RunDirectory $run -Event menu-ready
.\scripts\mark_perf_event.ps1 -RunDirectory $run -Event world-ready
```

PresentMon 2.x captures each frame, then the analyzer reports mean FPS, 1% low, 0.1% low, and p95/p99 frametime. Supply the official portable CLI executable path; the script writes the complete frame CSV inside the ignored run directory.

```powershell
.\scripts\capture_presentmon.ps1 `
  -RunDirectory $run `
  -Scenario stationary-loaded-chunks `
  -PresentMonPath "$env:TEMP\BoundlessDiagnostics\PresentMon-2.6.0-x64.exe" `
  -DurationSeconds 180
```

The official PresentMon CLI documents process-ID capture, timed CSV, and v2 frame metrics: <https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md>.

## Tick, heap, GC, and chunk diagnostics

In the world, collect the following at each marked scenario boundary:

```text
/spark tps
/spark health show --memory
/spark gc
/spark tickmonitor --threshold-tick 50
/spark profiler start --timeout 180 --thread "Server thread"
/spark profiler stop --save-to-file
/sparkc profiler start --timeout 180
/sparkc profiler stop --save-to-file
/boundless perf
```

`/spark tps` gives rolling TPS and average/min/max/median/p95 MSPT. Spark's Forge client command uses `/sparkc`; the server profiler uses `/spark`. `/boundless perf` reports the latest 1,200 actual server tick durations including mean, p50, p95, p99, and max, plus a mean-tick-time TPS equivalent. `mark_perf_event.ps1` writes each structured sample to its own CSV and the event timeline; the analyzer and comparator consume those files. Spark TPS is labeled as measured rolling TPS, while Boundless Tweaks is labeled as mean-time-equivalent TPS.

For example, copy the values displayed by each command into the matching event:

```powershell
.\scripts\mark_perf_event.ps1 -RunDirectory $run -Event spark-sample `
  -MeanTps 20 -AverageMspt 8.5 -P50Mspt 7.0 -P95Mspt 12.0 -P99Mspt 18.0 -MaxMspt 42.0 `
  -Note "stationary-loaded-chunks start"

.\scripts\mark_perf_event.ps1 -RunDirectory $run -Event tick-sample `
  -MeanTps 20 -AverageMspt 8.5 -P50Mspt 7.0 -P95Mspt 12.0 -P99Mspt 18.0 -MaxMspt 42.0 `
  -Note "values copied from /boundless perf; TPS is mean-time equivalent"
```

Use `menu-ready` and `world-ready` events at the human-visible endpoints. The analyzer reports these elapsed from the capture start separately from log-derived ModLauncher and Minecraft signals. Re-run `analyze_perf_capture.py` after adding manual samples.

Enable `/spark gcmonitor` during a diagnostic pass or use JFR to capture heap/GC history. The capture script's optional JFR includes execution stacks, Minecraft tick/chunk-generation events, heap summaries, and GC pauses. For chunk work, profile the server thread while following the fixed exploration route; capture JFR chunk-generation events when present. Loaded chunk counts and exact F3 coordinates should be recorded with `f3-sample`.

Spark command details: <https://spark.lucko.me/docs/Command-Usage> and <https://spark.lucko.me/docs/guides/TPS-and-MSPT>.

## Analysis and comparison

```powershell
python scripts\analyze_perf_capture.py $run
python scripts\compare_perf_captures.py `
  "auditoria/testes/runs/2026-11-13/baseline-stationary-r1" `
  "auditoria/testes/runs/2026-11-13/baseline-stationary-r2" `
  --output-dir auditoria/performance/p0.1/comparisons/stationary-r1-r2
```

The comparator reports whether scenario, direct JAR hashes, and configuration fingerprints match its first run. A mismatch is visible in the CSV; never attribute a difference to a mod change when the other settings or route also changed.

## Result fields

Each curated comparison includes scenario, commit, runtime mod count, startup/menu/world-ready times, mean FPS, 1%/0.1% lows, frametime p95/p99, Spark TPS/MSPT, Boundless Tweaks tick p95/p99, `Can't keep up` backlog warnings, JFR tick-window averages, GC pause totals, chunk-generation event counts, and server-thread stack samples. `Can't keep up` values are accumulated backlog between warnings, not individual MSPT.
