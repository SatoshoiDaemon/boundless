# Boundless baseline v0.1.0

**Snapshot date:** 2026-11-13  
**Runtime:** Minecraft 1.20.1, Forge 47.4.28, Java 17 (audit runtime: 17.0.15)  
**Manager/distribution platform:** CurseForge

## Inventory counts

| Measure | Baseline |
|---|---:|
| External JAR files directly under `mods/` | 425 |
| Unique IDs in the Forge runtime table | 491 |
| Dependency declarations in the audit inventory | 1,160 |
| CurseForge mod records in local profile metadata | 412 |
| Distinct installed JARs resolved to one CurseForge project/file pair | 411 |
| Installed mod JARs without a verified CurseForge `projectID`/`fileID` | 14 |

The 425/491/1,160 counts were checked against the current `mods/` directory, `auditoria/inventario_mods.csv`, and `auditoria/dependencias_mods.csv`. Forge is included among the 491 runtime IDs and is separately classified as a loader component in the canonical manifest. The local profile has 412 mod records but 411 distinct installed filenames because two records refer to the same GeckoLib JAR. The audit's CurseForge fingerprint matches one exact installed-file record; the other record is not used. `auditoria/AUDITORIA.md` and `auditoria/FASE2_INVESTIGACAO.md` contain the underlying scope and interpretation.

## Reproduction status

**Incomplete.** The CurseForge profile metadata resolves 411 distinct installed JARs to project/file IDs. Fourteen installed JARs lack a verified pair in the available profile metadata. Some have an official homepage in their embedded metadata; the canonical manifest leaves project/file IDs null unless they were actually available. The custom `combatroll-hudfix-1.1.1.jar` has source files under `patches/combatroll-hud-compat/`, but the local build script depended on a different launcher's private library layout and is not included as a working build recipe.

The current instance also has third-party resourcepacks and shaderpacks in the launcher folders. Their redistribution conditions have not been reviewed, so they are excluded from Git and from the export allowlist. The `config/pulse-trims/pack/` files are retained with the configuration; the CurseForge profile identifies the owning Pulse Trims add-on. The current baseline therefore does not guarantee a fresh install that matches every visual or local runtime component.

CurseForge profile metadata reports `allowModDistribution: false` for 25 profile records. Because one filename is duplicated, 24 selected records map to distinct installed artifacts with that flag. Those values are preserved per artifact in the manifest. They are not interpreted as a license grant; the package does not contain any of those JARs.

## Source records

- `auditoria/inventario_mods.csv`: runtime IDs, names, versions, artifact references, and audit fingerprints.
- `auditoria/dependencias_mods.csv`: declared dependency ranges, sides, and source manifests.
- `minecraftinstance.json`: local CurseForge profile metadata used to extract exact project/file IDs and official URLs; intentionally ignored and not copied into the repository.
- Installed `/mods/*.jar`: SHA-256 values were calculated locally. The JARs themselves are intentionally not committed.

The generated `manifests/dependencies.json` omits profile GUIDs, machine-specific paths, local timestamps, and personal client state. CurseForge IDs and URLs are copied only from the instance metadata or a JAR's own declared homepage.

## Validation scope

Static validation checks the schema, audit counts, SHA-256 syntax, CurseForge metadata consistency, and required dependency targets against runtime IDs, loader IDs, and documented aliases. Installed-file validation compares each JAR's path and SHA-256 with the lock data. These checks do not prove semantic version-range satisfaction or launch/runtime compatibility; the original audit also notes that a separate semantic resolver was not run.

CI runs only static Python validation and the script unit tests. It does not need mod JARs or run Minecraft.
