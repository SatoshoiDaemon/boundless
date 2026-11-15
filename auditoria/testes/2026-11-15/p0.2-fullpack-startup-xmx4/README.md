# Full pack startup and idle menu — Xmx 4 GiB

Offline clone of the current Boundless instance; Forge 47.4.28 / Minecraft 1.20.1, JDK 17.0.12, 508 runtime mods from 439 direct mod JARs. No world was opened. The client reached the main menu with ModernFix logging `Game took 350.012 seconds to start`, then remained at the menu until the 12-minute JFR recording completed. It exited cleanly at 13 min 57 s.

## Measurements

- Heap: Xms 1 GiB, Xmx 4 GiB. `jcmd GC.heap_info` at the menu showed 3.81 GiB used of 4 GiB and 510 MiB metaspace used.
- Startup: 350.012 s to the ModernFix startup marker (5 min 50 s).
- Process capture: 391 samples over 832.3 s, every 2 s. Working-set p95/peak 6.38/6.47 GiB; private-bytes p95/peak 8.78/8.96 GiB; physical RAM minimum 225 MiB free.
- GC (12-minute JFR): 323 collection events, 16.91 s total pause, 366 pause phases, p95 117.8 ms, p99 334.1 ms, maximum 2.789 s. Heap use at GC p95 was 3.85 GiB before and 3.69 GiB after.
- Startup allocations: main thread allocated 47.48 GiB over 723 s (about 67 MiB/s). JFR allocation samples cluster in pack/resource lookup, config file watching, model baking and ImmediatelyFast's buffer source. No server tick or chunk-generation events were recorded because the run remained at the main menu.
- Functional log check: zero `[ERROR]` lines; no Dayzombie Rebooted configuration exception and no Illage & Spillage bone/axe attribute error.

The run met the six-minute startup timer target but missed the one-second maximum GC-pause goal. Xmx 4 GiB left little host RAM free and kept the heap nearly full, so it is not a validated setting for a loaded world.

The P0.1 startup record had 505 runtime mods, a 424.132 s startup timer, working-set p95/peak of 8506/8783 MiB, and free-RAM median/minimum of 809/87 MiB. This comparison is descriptive: mod count, settings, recording setup and filesystem-cache state differ, so the 74.1 s shorter timer and lower working set cannot be attributed to heap alone.
