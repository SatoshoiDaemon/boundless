# Historical in-world run — power outage

This session launched a 492-mod Forge 1.20.1 pack and entered an existing world. Its retained observations span about 21:10–21:44 on 13 November 2026; the exact shutdown time was not captured. The user confirmed that a power outage ended the session. It was not a Minecraft crash. The earlier `JumpAnimation` crash in the static audit happened in a separate session.

## Startup and world entry

- ModLauncher began at 21:10:22. Minecraft logged `Game took 384.251 seconds to start` at 21:16:42.
- ReactiveMusic emitted the first `MAIN_MENU_` signal at 21:15:15, 293 s after ModLauncher. This signal is not an exact interactive-menu timestamp.
- The integrated server started at 21:18:31, about 489 s after ModLauncher. Spawn preparation advanced from 0% to 98% in 59 s. A later F3 screenshot confirms the player was in-world.
- Largest recorded deferred startup tasks: ReactiveMusic 14.90 s, Graveyard 14.13 s, and Irons' Lib 13.27 s. These durations do not explain the entire startup.

## Server ticks and frame point

- 30 `Can't keep up` warnings: mean 34.940 s, median 17.092 s, p95 109.631 s, maximum 164.633 s / 3,292 ticks behind. These are accumulated backlog intervals, not individual MSPT.
- ModernFix reported one 40.955 s server tick. Its captured stack traversed Enderman target selection and `EntityTickList`; this confirms that path was active during the stall but does not assign the full delay to one mod.
- F3 at 21:21:39 showed 33 FPS and 207 ms/tick (about 4.83 ticks/s equivalent), heap 6,110/10,240 MiB, allocation 203 MiB/s, GPU 5%, 942 client chunks, 2,244 server chunks, 130 entities and 72 monsters. It is one point, not an average or a frame-time distribution.
- EMI reloads took 47.668 s and 79.399 s; runtime resource generation took 41.233 s. They are confirmed long tasks, but no trace ties them to a specific frame or every server stall.

## Limits and preservation

The old `latest.log` was replaced by the next launch before the raw file was archived. This record preserves the measured timings, warning series, F3 screenshot/point, and known interpretation. It has no exact historical commit, direct-JAR lock, config lock, seed, route, PresentMon recording, or repeated trials. Therefore it is a symptom baseline and is not a controlled comparison with the 505-mod startup.
