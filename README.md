# Boundless

Boundless is a CurseForge-managed Minecraft Forge instance. This repository records its configuration, technical audits, dependency metadata, project-owned patches, and the source for future Boundless components while keeping the live instance in place.

## Baseline

- Minecraft **1.20.1**
- Minecraft Forge **47.4.28**
- Java **17** (the audit observed runtime 17.0.15)
- Baseline date: **2026-11-13**
- Audited inventory: **425 external JARs**, **491 unique runtime mod IDs**, and **1,160 declared dependency edges**

The counts are recorded in [docs/baseline-v0.1.0.md](docs/baseline-v0.1.0.md) and checked against the audit CSVs by the scripts. The canonical dependency data is [manifests/dependencies.json](manifests/dependencies.json). It contains hashes and available CurseForge metadata, but it is **not a claim that the full instance can already be reproduced**.

CurseForge profile metadata has 412 mod records but resolves to 411 distinct installed JARs; two records name the same GeckoLib file, and the audit fingerprint identifies the matching project/file record. Fourteen JARs have no verified `projectID`/`fileID` in the available profile metadata; the export script refuses to produce a package while those sources remain unresolved. Third-party shaderpacks and resourcepacks are also excluded until redistribution terms are checked.

## Reproducing and validating the installation

Use the CurseForge application as the supported manager and distribution platform. The repository does not contain the third-party mod JARs. Once every dependency has a verified CurseForge file reference or an individually approved acquisition method, build or export through the CurseForge workflow and install through the CurseForge application.

The ignored `minecraftinstance.json` is local CurseForge profile metadata. To refresh the canonical data after an approved instance change, run from the instance root:

```powershell
python -m scripts.build_manifest --instance-root . --profile minecraftinstance.json
```

Static manifest and dependency checks do not need installed JARs:

```powershell
python -m scripts.validate_manifest --static
```

Compare the manifest with the current installed JARs:

```powershell
python -m scripts.validate_manifest --compare-installed --instance-root .
```

Run the script tests with Python's standard library:

```powershell
python -m unittest discover -s tests -v
```

The CurseForge package script creates a ZIP with `manifest.json` and `overrides/`, as required by the [CurseForge export guidance](https://support.curseforge.com/support/solutions/articles/9000198500-exporting-a-modpack-for-curseforge-project-submission). It only copies `config/`, `defaultconfigs/`, `kubejs/`, and `datapacks/`; it never copies `mods/`, `resourcepacks/`, `shaderpacks/`, saves, logs, or profile metadata. It requires an explicit author field and a complete set of CurseForge project/file IDs:

```powershell
python -m scripts.export_curseforge --instance-root . --author "<pack author>" --output dist/Boundless-0.1.0.zip
```

This export is currently blocked by the fourteen JARs without verified CurseForge IDs and by the unreviewed third-party resource/shader-pack terms. It will not silently create an incomplete pack.

## Contribution and CI

Keep instance-required files in their Minecraft paths. Put new code and documents in the repository's project-owned directories. For a dependency change, update the CurseForge instance first, regenerate the manifest, review the SHA-256 and source changes, then run both static and installed-file validation. Do not commit saves, logs, profile metadata, third-party JARs, or third-party resource/shader packs.

GitHub Actions validates the checked-in manifest and dependency graph and runs the script tests with the Python standard library. It does not download dependencies, use proprietary JARs, or launch Minecraft. When a Java component is added, document and add its tests separately; no Minecraft client test runs in CI.

## Planned components

- `development/boundless-compat/`: future Java 17 Forge mod project; no mod implementation is included in this baseline.
- `development/complementary-boundless/`: future Complementary Boundless shaderpack variant; shader files are not modified here.
- `patches/`: project-owned compatibility patch sources. The existing Combat Roll HUD patch source snapshot is retained separately from its ignored local build outputs.
- `resources/`: project-owned resources after their provenance and license are documented.
- `scripts/`: dependency validation and CurseForge packaging utilities.

## Redistribution limits

This repository does not redistribute third-party mod JARs, shaderpacks, or resourcepacks. The CurseForge metadata records the installed project/file IDs and source URLs when they are available; local profile identifiers and absolute machine paths are omitted. The CurseForge `allowModDistribution` value is recorded as source metadata and is not treated as a substitute for a license review. Any third-party asset must be checked against its license and the applicable CurseForge rules before packaging. No Modrinth `.mrpack` is generated.

No repository-wide open-source license has been selected. Do not assume that code or assets in this repository are licensed for reuse beyond the rights stated in their own metadata.
