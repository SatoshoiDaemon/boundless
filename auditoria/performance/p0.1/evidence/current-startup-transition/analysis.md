# Performance capture: p01-current-20261114

- Scenario: `client-startup`
- Commit: `57a230b6039f94ec635381246613faa702a3f033`
- Status: `complete`

## Startup and world loading

- Loaded runtime mods: 505
- Minecraft startup timer: 424.13 s
- First main menu signal: 344 s from launch
- Human menu-ready mark: n/d s from capture start
- Integrated server start: n/d s from launch
- World `Done` marker: n/d s from launch
- Human world-ready mark: n/d s from capture start
- Spawn progress: n/d% to n/d% in n/d s


## Startup log errors

- Severity-tagged messages: 377 ERROR, 836 WARN.
- `172×` Entity illageandspillage:bone has no attributes
- `172×` Entity illageandspillage:axe has no attributes
- `3×` Unable to parse animation: idle
- `2×` Error occurred applying transform of coremod coremods/field_to_method.js function biome
- `1×` Mixin config astikorcartsredux.mixins.json does not specify "minVersion" property
- `1×` Mixin config pulse-trims.mixins.json does not specify "minVersion" property
- `1×` Mixin config mixins.satin.client.json does not specify "minVersion" property
- `1×` Mixin config fabric-item-api-v1.client.mixins.json does not specify "minVersion" property

## CPU and memory

- Java process CPU mean/p95/max: 33.23/62.12/73.45% of total logical CPU; system CPU while Java ran mean/p95/max: 63.58/100.00/100.00% (whole capture: 55.95% mean).
- Java working-set p95/max: 8506.25/8783.17 MiB; free physical RAM median/min: 808.89/87.16 MiB.
- Short pressure sample n=8: committed memory mean/max 94.00/94.00%; available RAM mean/min 1005.12/743.00 MiB; page reads/sec p95/max 3288/3288.

## Frametime

- `frametime-startup-transition-232736.csv` (startup-transition, 6917 frames, DisplayedTime/MsBetweenDisplayChange): mean 57.69 FPS; 1% low 13.20; 0.1% low 5.85; frametime p95/p99 19.26/29.81 ms. Context: 120 s PresentMon capture at 23:27:36 while PID 9248 remained alive. Display state was not verified after the last screenshot at 23:21 (Mojang loading screen); log had a MAIN_MENU music signal at 23:19:24 and no world load. Treat as startup-transition frames, not stable-menu or gameplay performance.

## Tick backlog and JFR

- Log backlog warnings: 0; mean/p95/p99/max n/d/n/d/n/d/n/d ms. These are accumulated delays between warnings, not individual MSPT.
- JFR ServerTickTime window averages: n=0, mean/p95/p99/max n/d/n/d/n/d/n/d ms.
- GC pause sum from GarbageCollection events: n/d s; GC event count 0.
- JFR chunk-generation events: 0.
- JFR execution samples for thread `ReactiveMusic Player Thread`: n=4; most frequent stack frames: rm_javazoom/jl/decoder/LayerIIIDecoder.decode, rm_javazoom/jl/decoder/LayerIIIDecoder.decodeFrame, rm_javazoom/jl/decoder/Decoder.decodeFrame, rm_javazoom/jl/player/advanced/AdvancedPlayer.decodeFrame, rm_javazoom/jl/decoder/LayerIIIDecoder.dequantize_sample.
- JFR execution samples for thread `Render thread`: n=2; most frequent stack frames: net/minecraftforge/client/extensions/IForgeBakedModel.getRenderPasses, net/minecraft/client/renderer/entity/ItemRenderer.m_115143_, net/minecraft/client/gui/GuiGraphics.m_280405_, net/minecraft/client/gui/GuiGraphics.m_280053_, net/minecraft/client/gui/GuiGraphics.m_280480_.
