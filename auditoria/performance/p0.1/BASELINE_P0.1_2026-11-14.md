# Boundless P0.1 — performance baseline and diagnostics

**Status:** diagnostic and comparison infrastructure is implemented. Historical in-world symptoms and one current-pack startup-transition capture are measured. The current UI session did not reach a recorded world-ready marker, so world/tick/chunk benchmark passes remain for the next user-side run. The earlier in-world run ended because of a power outage, not a game failure. No performance improvement is claimed.

## Decision summary

The confirmed P0 symptom is integrated-server tick starvation: the historical run emitted 30 `Can't keep up` backlog warnings, with a 34.940 s mean and 164.633 s maximum. ModernFix recorded one 40.955 s server tick. The captured server-thread stack for that stall was in Enderman target selection and entity-list traversal. This confirms entity AI/lookup work was executing during a catastrophic server tick. It does not prove one mod caused every warning.

The latest F3 image shows 33 FPS at one instant while the integrated server reported 207 ms/tick, equivalent to about 4.83 ticks/s at that instant. This is a severe server-side stall during a low reported GPU-utilization point (5%). It makes server tick work the best-supported primary explanation for the freezing/teleporting symptom; it does not establish average FPS or GPU load across the run.

The run also had confirmed long client/resource tasks: an EMI reload took 47.668 s and later 79.399 s; runtime resource generation took 41.233 s. These coincide with a stutter-prone session but do not identify which task caused a particular frame or tick delay.

The separate 505-mod launch recorded `Game took 424.132 seconds to start`. Its first `ReactiveMusic MAIN_MENU_` signal appeared 344 s after ModLauncher, but the human-visible menu-ready endpoint was not marked: the last available screenshot still showed the Mojang loading screen. No world was loaded in the captured log. A 120 s PresentMon transition sample produced 57.69 mean FPS, 13.20 1% low, 5.85 0.1% low, p95/p99 frametime 19.26/29.81 ms, and a 235.43 ms maximum frame. This is a real transition-state frame sample, not a stable menu or gameplay average, and it does not identify the cause of the tail frames.

The same launch showed strong host memory pressure: Java working set p95/max 8.51/8.78 GiB, available physical memory fell to 87 MiB in the two-second series, and a separate eight-sample pressure window reported 94% commit with paging counters peaking at 29,705 pages/s. Paging counters may include file-backed reads. This confirms memory pressure during that startup window; it does not establish GC as the source of the in-world tick stalls. The 30 s post-startup JFR had only six execution samples and no server-tick, GC, heap-summary, or chunk-generation events.

## Execution states

| Run | Runtime state | Evidence | Interpretation |
| --- | --- | --- | --- |
| Historical in-world run, observations 13/11/2026 21:10–21:44 | 492 Forge runtime mods; shaderpack active | Startup log; F3 screenshot; 30 backlog warnings; ModernFix watchdog stack | The world was running. The exact shutdown time was not recorded; the user confirmed a power outage ended this execution. Do not classify it as a Minecraft crash. |
| Current-pack launch, 13/11/2026 23:09–23:32 | 505 Forge runtime mods; Spark 1.10.53, EntityCulling 1.12.1, and Boundless Tweaks 0.1.0 present | 424.132 s startup timer; 120 s PresentMon transition capture; CPU/memory samples; 30 s JFR; JAR/config/shader fingerprints | No menu-ready mark or world load. User stopped Computer Use with physical Escape; Minecraft remained responsive. `/boundless perf` and in-world profiling were not collected. |

The historical measured state predates Spark 1.10.53 and the EntityCulling 1.12.1 update. Its old Forge log was not copied to a run folder before the current launch replaced `logs/latest.log`; the exact backlog series and single F3 point are preserved in the curated CSVs below. The capture script now copies the live log at run close and locks all current JAR/config hashes.

## Environment and conditions

- Windows 11; Intel Core i5-6600, 4 cores/4 threads at 3.30 GHz; Radeon RX 480; 12,786,397,184 bytes RAM (11.91 GiB).
- Microsoft OpenJDK 17.0.15; Minecraft 1.20.1; Forge 47.4.28.
- Historical run: 492 runtime mods; measured before current commit `57a230b` was created and before current JAR/config locks were added. The exact historical working-tree commit and dirty state were not captured.
- Current pack: the loader enumerated 505 runtime mods from 438 direct JARs. The curated run metadata locks each JAR, every `.toml`, `.properties`, `.json`, `.cfg`, and `.txt` file in `config/`, `options.txt`, and the selected 633-file shaderpack.
- Display: 1920×1080; Fancy; render distance 12; simulation distance 8; Complementary Reimagined r5.9.3 + Euphoria Patches 1.10.5 active; custom Popular profile and real-time dynamic lighting.
- Historical save seed, route, camera, and repeat count were not recorded. Treat it as a valid symptom observation, not a controlled A/B benchmark.

## Measured evidence

### Startup and world entry

- Historical ModLauncher timestamp: 21:10:22. Minecraft logged `Game took 384.251 seconds to start` at 21:16:42, approximately 6 min 24 s to its startup marker.
- ReactiveMusic emitted its first `MAIN_MENU_` signal at 21:15:15, about 4 min 53 s after ModLauncher. This is a music-state signal, not the exact moment the menu became interactive.
- The integrated server started at 21:18:31 (about 8 min 09 s after ModLauncher). Spawn preparation progressed from 0% at 21:18:39 to 98% at 21:19:38. The screenshot later confirms the player was in-world.
- Largest deferred tasks in that run included ReactiveMusic 14.90 s, Graveyard 14.13 s, and Irons' Lib 13.27 s. They are measured tasks; these durations alone do not explain the full startup.
- Current-pack startup: 505 runtime mods; `Game took 424.132 seconds to start`, and the first menu-music signal arrived at 344 s after ModLauncher. The timer is 39.881 s longer than the historical 492-mod timer, but JARs/configuration and machine pressure were not held constant, so this is descriptive rather than a mod-count attribution. The interactive menu-ready time remains unknown.
- The longest deferred startup tasks in this launch were Alex's Mobs 13.62 s, ReactiveMusic 6.883 s, and Nether Chested 4.43 s. Runtime resource generation for 10 packs took 8.908 s; 82 shader sources loaded in 426.682 ms. These measured tasks are too short to explain the full 424 s on their own.

### Integrated-server ticks

- Historical warning series: **30 events**, mean **34.940 s**, median **17.092 s**, p95 **109.631 s**, p99/max **164.633 s** of accumulated lag between `Can't keep up` reports. These are backlog intervals, not individual MSPT.
- Maximum warning: **164.633 s / 3,292 ticks behind** at 21:42:36.
- ModernFix watchdog: one server tick took **40.955 s** at 21:20:37.
- Watchdog stack: `EnderMan$EndermanLookForPlayerGoal` → target-condition/entity query → `EntityTickList`; Forge's `IForgeItemStack.isEnderMask` hook was on this path. The confirmed subsystem is per-tick entity targeting/iteration during that stall. This evidence does not isolate a specific mod's share or explain all 30 warnings.
- One screenshot sample: F3 reported **207 ms/tick**. This is not a mean or p95.
- The current 505-mod launch produced no world-ready marker, `Can't keep up` warning, or server-tick sample. Its 30 s post-startup JFR contained six execution samples (four on ReactiveMusic's audio thread and two on Render thread), but no `ServerTickTime`, GC, heap-summary, or chunk-generation event. This window is too short and sparse to profile gameplay.

### Client frames, memory, and chunks

At 21:21:39, F3 showed **33 FPS**, heap **6,110 / 10,240 MiB**, allocation **203 MiB/s**, GPU utilization **5%**, client chunks **942**, server chunks **2,244**, spawn chunks **289**, and **130 total entities / 72 monsters**. The equivalent `1,000 / 207 ms` is 4.83 ticks/s for that moment only.

The 10 GiB heap cap leaves about 1.91 GiB of the host's 11.91 GiB for Windows, CurseForge, graphics drivers, and other applications. The historical in-world run has no memory time series; the later startup capture confirms host memory pressure, but it does not connect that pressure to a GC pause or the historic world stalls. In a separate older 213 s JFR window, recorded GC pauses totalled about 254 ms, while server-tick interval averages were very high (mean 4.798 s, p95 28.2 s, maximum 33.3 s). That window shows GC did not account for those observed stalls; it is from a different mod state and is not a substitute for current-run GC data.

Earlier JFR samples showed work in `PalettedContainer`/`LevelChunk`, `EntitySectionStorage`, `ChunkHolder`/`ServerChunkCache`, and `DistanceManager`. No `minecraft.ChunkGeneration` event was captured in that window. This confirms chunk-management work occurred in the sampled stacks; it does not confirm that fresh terrain generation dominated the reported exploration stutter.

The current 120 s transition capture analyzed 6,917 displayed-frame intervals: **57.69 mean FPS**, **13.20 1% low**, **5.85 0.1% low**, **19.26/29.81 ms p95/p99**, and **235.43 ms maximum**. It began at 23:27:36 after the last observed screenshot (Mojang loading screen at about 23:21); display state was not verified then, and there was no world load in the log. Treat this as startup-transition data only. It confirms severe frame-time outliers in that window, not their cause or stable in-game FPS.

During the same launch, Java working set was **8.51 GiB p95 / 8.78 GiB max**. Available physical RAM reached **87 MiB minimum** in the two-second series. An eight-sample follow-up showed **94% committed memory**, **743 MiB minimum available**, and peaks of **29,705 pages/s**, **3,288 page reads/s**, and **23,261 pages output/s**. These confirm host memory pressure; Windows paging counters can include file-backed activity. GC was not measured during the window in which the frame tails were captured.

System CPU while Java was present averaged **63.58%**, with **100% p95/max** across four logical processors. Java itself averaged **33.23%** of total machine capacity and peaked at **73.45%**. Full-host CPU saturation is observed, but this does not isolate Minecraft's server or render thread as the source.

### Renderer, shader, and resource reloads

- The active visual stack was confirmed in the F3 screenshot and Oculus config.
- Historical render-thread snapshot was inside Xaero Minimap info rendering and EmojiFul's emoji formatting. This is one stack sample, so it is a client profiling lead, not a measured share of frame time.
- The log recorded a 47.668 s EMI reload, a later 79.399 s EMI reload, and 41.233 s runtime resource generation. The long reloads are real; attribution of an individual low-FPS frame or server tick remains unverified.
- Oculus and several renderer extensions modify Embeddium internal classes; the log specifically reports shared targets and an Oculus modification of `SodiumGameOptions`. This confirms a large shared patch surface and raises compatibility risk. It does not prove a renderer conflict or performance loss.
- DynamicFPS and FPS Reducer both provide idle/background FPS reduction. This is overlapping policy outside active exploration, not a confirmed in-world conflict.

### Current startup-log errors

The captured 505-mod startup log contains **377 ERROR-tagged lines** and **836 WARN-tagged lines**. Of the errors, **172 each** report that `illageandspillage:bone` and `illageandspillage:axe` have no attributes; 15 Mixin configs lack `minVersion`; two `field_to_method.js` biome transforms fail; four animations fail to parse; five models fail to load; and the remaining messages cover one book, one Embeddium mixin-taint notice, one image-mask mismatch, one BOP heavy-leaf texture generation error, one Fabric-API/Connector warning, one reload-listener timing warning, and one online version-check exception. These are confirmed loader/content diagnostics for Boundless Fix and Boundless Compat. No crash report was produced for this startup and no world was loaded. The repeated entity-attribute messages may add some loader/log work, but their effect on startup duration or gameplay has not been measured.

## Gargalos e candidatos

### Confirmados

1. **Integrated-server tick loop severely overloaded.** The backlog series and 40.955 s watchdog tick establish the scale. Entity target search/list traversal was active during that watchdog tick.
2. **Long startup.** The 492-mod run took 384.251 s to Minecraft's startup marker; the world server began at about 8 min 09 s.
3. **Long reload work.** EMI/resource operations lasted tens of seconds during the session.
4. **One low-frame / low-server-rate point.** 33 FPS and 207 ms/tick occurred together; the image does not supply run averages or lows.
5. **Renderer patch overlap.** Multiple mods touched Embeddium internals in the current mod set; this is a verified compatibility surface, not a confirmed slowdown.
6. **Startup-transition frame-time outliers.** PresentMon measured 13.20/5.85 FPS 1%/0.1% lows in the 120 s sample, with a 235 ms worst displayed interval. No stable-menu or gameplay frame baseline was captured.
7. **Host memory pressure during current startup.** Low available RAM and 94% commit were measured; the relationship to historic world stalls is unmeasured.

### Candidatos principais, ainda sem atribuição exclusiva

1. **Entity density/AI and entity queries** remain the strongest in-world tick candidate because they appear in the 40.955 s stack and the screenshot had 72 monsters / 130 entities. The Enderman search path and entity-list traversal were active; no evidence isolates which optimization mod changes their cost. Use Spark server-thread profiles and `/boundless perf` on stationary and exploration routes.
2. **Chunk management and terrain generation** remain strong exploration candidates based on earlier JFR stack samples and the user symptom. No captured profile contained a `ChunkGeneration` event; profile a virgin route and a pre-generated route separately.
3. **Host memory pressure** is observed in current startup, with <100 MiB free in one sample and Windows commit at 94%. Whether this pressure causes GC pauses or in-world tick/frame stalls is unverified. Capture heap/GC and paging concurrently during an in-world pass before changing heap.
4. **CPU contention** is plausible because whole-host CPU reached 100% while Java was active on a 4-thread host. A server-thread and render-thread profile is needed to separate single-thread saturation from other processes.
5. **Startup mod work and resource reloads** are measured, but the largest individual current deferred task was 13.62 s. These tasks cannot by themselves account for the 424 s startup; mark visible menu readiness and profile phases before disabling mods.
6. **Shader/dynamic-lighting cost and renderer mixins** may affect client frametime. The prior sampled GPU utilization was only 5%, but this is one point; collect stable PresentMon and `/sparkc` data before an explicit shader A/B.

## Prioritized next corrections

| Priority | Action | Expected impact | Risk |
| --- | --- | --- | --- |
| P0 | On the next interactive client session, mark actual menu-ready and world-ready, then collect Spark TPS, `/boundless perf`, heap/GC, and a server-thread profile | Very high diagnostic value for freezing/teleporting | Low; read-only measurement |
| P0 | Run three comparable stationary, pre-generated, and virgin-terrain captures with PresentMon and exact JAR/config locks | Separates server tick stalls from client frametime and chunk generation | Low; diagnostic only |
| P1 | Profile startup/current reload tasks by mod and capture heap/GC/free-RAM during the same run | High for 6-minute boot and reload pauses | Low; profiling overhead is isolated from baseline |
| P1 | Evaluate entity-heavy tick methods after profiles identify their share; then A/B one AI/entity change | High if the server-thread profile corroborates it | Medium; gameplay behavior can change |
| P2 | Validate renderer shared-target warnings and compare shader/real-time-lighting conditions using PresentMon | Medium for client stutter | Medium; visual behavior changes, keep the reference profile as control |
| P2 | Review 10 GiB maximum heap against captured GC and free-RAM data before adjusting memory settings | Potentially high on a 12 GiB host | Medium; changing Xmx may trade GC frequency against OS pressure |

No performance change is applied in this P0.1 phase. Boundless Tweaks 0.1.0 is confirmed in the current Forge modlist and adds a bounded 1,200-tick mean/p50/p95/p99/max sampler with mean-time TPS equivalent. The command was not sampled in-world. Chunk-specific optimizations remain assigned to Boundless Chunk Utils after profiles quantify generation/loading work.

## Versioned evidence

- [Reproducible benchmark protocol](BENCHMARK_PROTOCOL.md)
- [Optimization mod/version inventory](optimization-inventory.csv)
- [Historical F3 point sample](observed-f3.csv)
- [Historical 30-event backlog series](historical-tick-backlog.csv)
- [Historical F3 screenshot](../../../screenshots/2026-11-13_21.21.40.png)
- [Prior integrated tests and JFR notes](../../TESTE_INTEGRADO_2026-11-13.md)
- [Historical-to-current startup comparison](comparisons/startup-history-vs-current-2026-11-14/comparison.md) (JAR/config drift is marked; not a controlled A/B).
- [Curated current startup-transition evidence](evidence/current-startup-transition/analysis.md) (the raw log and 30 s JFR remain local and ignored; relevant PresentMon frames, JAR lock, and pressure series are versioned).
- [Curated historical power-outage evidence](evidence/historical-power-loss/analysis.md) (the old raw log was replaced by the newer launch before archiving; curated timings, F3 point, and backlog series are preserved).
- Full local capture: `auditoria/testes/runs/2026-11-13/p01-current-20261114/` (ignored to avoid duplicating raw logs and the JFR).
