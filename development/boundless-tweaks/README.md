# Boundless Tweaks

Boundless Tweaks owns general memory, CPU, startup and performance work. Version `0.1.0` adds a bounded, on-demand server tick distribution to complement Spark: `/boundless perf` reports the mean, median, p95, p99, maximum MSPT and equivalent TPS over the latest 1,200 processed server ticks.

The collector stores two nanosecond values per tick in a fixed 1,200-entry ring buffer. It does not log each tick, allocate per-tick objects, or write files during play. The measurement starts at the Forge server tick START event and ends at the lowest-priority END event. It therefore includes the server tick handlers between those boundaries; it does not measure client frame time.

## Build and install

Use JDK 17 and run `gradlew.bat jar`. The artifact is `build/libs/boundlesstweaks-0.1.0.jar`. Copy it into the Boundless `mods/` folder. The mod has no required dependency on Spark; Spark remains the profiler for locating expensive methods and subsystems.

## Runtime collection

Open a world and wait until the initial spawn-area load settles. `/boundless perf` reports the latest 1,200 completed integrated or dedicated server ticks. Capture the command output with the matching scenario and timestamp. Use `/spark tps` for Spark's rolling TPS/MSPT view and a Spark profile to identify what work occupies the server thread.
