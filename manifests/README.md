# Dependency manifest

`dependencies.json` is the canonical, metadata-only lock record for the current CurseForge-managed instance. It records installed external mod JARs, runtime mod IDs, embedded Jar-in-Jar libraries, Forge loader metadata, declared dependencies, SHA-256 hashes, and source/acquisition details when available.

The local `minecraftinstance.json` profile is an input to `python -m scripts.build_manifest`; it is not itself committed because it contains instance GUIDs, local paths, and client state. The canonical file records only project/file identifiers, official URLs, and non-personal status fields. The current profile contains 412 mod records for 411 distinct filenames; the duplicated GeckoLib filename is resolved by matching the audit fingerprint to the installed CurseForge file metadata.

`dependencies.json` is not the CurseForge export `manifest.json`. The latter is generated inside a ZIP with an `overrides/` tree by `python -m scripts.export_curseforge`. Export is blocked until every installed mod JAR can be represented by a verified CurseForge file ID or another explicitly approved acquisition method.
