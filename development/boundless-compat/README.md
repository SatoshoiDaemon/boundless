# Boundless Compat

Boundless Compat is the first mod authored for the Boundless RPG instance. It adds narrowly scoped compatibility fixes and diagnostics for the versions used by the pack. Version 0.1.0 targets Minecraft 1.20.1, Forge 47.4.28, and Java 17.

## JumpAnimation 2.0.0 fix

On the client, a Mixin targets only `JumpAnimationClient.isPlayerInSurvival(LocalPlayer)`. It is selected only when the installed mod ID is `jumpanimation` at exactly version `2.0.0`. When the player's game mode is not initialized, the helper returns `false`, so JumpAnimation skips its survival-only behavior for that callback. Once a game mode exists, the original method continues unchanged. The patch does not intercept keyboard events or modify player controls.

The client config `config/boundlesscompat-client.toml` contains `compat.jumpAnimationNullGameModeGuard`, enabled by default. Mixin selection happens during startup, so the compatible-version gate is fixed for that launch; the config value is checked by the injected guard and can disable its behavior without attempting to add or remove a Mixin at runtime.

## Build and install

With a JDK 17 installation, run `gradlew.bat clean build` from this directory. The installable artifact is `build/libs/boundlesscompat-0.1.0.jar`. Copy that JAR into the Boundless instance's `mods/` directory. JumpAnimation is optional; without it, the compat mod loads and the patch is not selected.

The Forge `runClient` configuration can be used for development startup checks. To launch against the instance's exact JumpAnimation and Player Animator versions, run `gradlew.bat runClient -PtestWithJumpAnimation`; this development-only profile remaps those local JARs and does not add them to the Boundless Compat artifact or its required mod list. The unit tests cover the guard's enabled, disabled, null, and normal-state decisions. A successful compile or unit test does not by itself prove the full Minecraft client runtime behavior.

Use `/boundless diagnose` in game to print Minecraft, Forge, Java, Boundless Compat, selected compatibility-mod versions, and the JumpAnimation patch gate/config state.

## Planned work

- **v0.2 — Content repairs:** investigate Mowzie's Mobs Grottol models, Born in Chaos animation definitions, and broken recipes, advancements, loot tables, and tags. Prefer internal datapack or resourcepack fixes when sufficient.
- **v0.3 — Performance diagnostics:** measure the reported extreme integrated-server tick delays, including records up to 111.641 seconds, and inspect chunk generation, entities, AI, and tick duration.
- **v0.4 — Targeted optimizations:** implement fixes based on measured bottlenecks, prioritizing world generation, entities, and mod integrations while preserving intended visuals and gameplay.
