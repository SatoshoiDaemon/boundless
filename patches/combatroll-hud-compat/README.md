# Existing Combat Roll HUD compatibility patch

This is a source snapshot of the patch that was already installed in the Boundless instance as `combatroll-hudfix-1.1.1.jar`. The Java and resource files were copied from the local `local-patches/hud-compat/` source tree; the original tree, instance JAR, logs, test worlds, backups, and build artifacts were left untouched.

No new compatibility behavior was implemented for baseline v0.1.0. The patch JAR is excluded from Git. Its existing local build script references a Freesm Launcher library path and Forge 47.4.10, so this source snapshot is not yet a standalone reproducible build. The current instance uses Forge 47.4.28. A future build setup must resolve those inputs deliberately before this patch is packaged or published.

The patch metadata declares MIT. No third-party source or binary is copied here. This source snapshot is retained for audit and future build work; the CurseForge export script does not package it.
