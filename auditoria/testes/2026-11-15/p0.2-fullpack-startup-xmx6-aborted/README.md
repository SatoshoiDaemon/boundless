# Full pack startup — 6 GiB heap (aborted)

Clone-only offline Forge client startup; 439 mod JARs, Forge 47.4.28, Java 17.0.12, Xms 1 GiB / Xmx 6 GiB. No world was opened. The process reached the resource/model reload phase, then became unresponsive as physical memory pressure escalated. It was closed from the isolated clone before any world save was involved.

The 2-second process capture recorded 145 samples. Peak private bytes were 11.3 GiB and physical RAM reached 61.7 MiB free. The JFR and GC options were mistakenly placed after the BootstrapLauncher main class and were ignored as game arguments; this run has memory telemetry and logs only, no JVM profile.
