"""Build the metadata-only Boundless dependency manifest from the live instance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = Path("auditoria/inventario_mods.csv")
DEFAULT_DEPENDENCIES = Path("auditoria/dependencias_mods.csv")
DEFAULT_OUTPUT = Path("manifests/dependencies.json")
ENVIRONMENT_IDS = ["minecraft", "java", "javafml", "lowcodefml", "fabric", "fabricloader"]
DEPENDENCY_ALIASES = {
    "cloth-config": "cloth_config",
    "fabric-api": "fabric_api",
    "fabric-api-base": "fabric_api_base",
    "fabric-resource-loader-v0": "fabric_resource_loader_v0",
}


def read_semicolon_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=";"))


def split_reported_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"\s+\|\s+", value) if part.strip()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def as_nonnegative_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def official_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.startswith(("https://", "http://")):
        return candidate
    return None


def jar_homepage_from_path(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            return jar_homepage_from_archive(archive)
    except (OSError, zipfile.BadZipFile):
        return None


def jar_homepage_from_bytes(data: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return jar_homepage_from_archive(archive)
    except (OSError, zipfile.BadZipFile):
        return None


def jar_homepage_from_archive(archive: zipfile.ZipFile) -> str | None:
    names = {name.lower(): name for name in archive.namelist()}
    fabric_path = names.get("fabric.mod.json")
    if fabric_path:
        try:
            metadata = json.loads(archive.read(fabric_path).decode("utf-8"))
            contact = metadata.get("contact", {})
            if isinstance(contact, dict):
                candidate = official_url(contact.get("homepage"))
                if candidate:
                    return candidate
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            pass

    mods_toml_path = names.get("meta-inf/mods.toml")
    if mods_toml_path:
        try:
            text = archive.read(mods_toml_path).decode("utf-8", errors="replace")
            for match in re.finditer(r"(?im)^\s*displayURL\s*=\s*[\"']([^\"']+)[\"']", text):
                candidate = official_url(match.group(1))
                if candidate:
                    return candidate
        except (OSError, KeyError):
            pass
    return None


def scan_embedded_archives(mods_directory: Path) -> list[dict[str, Any]]:
    """Index embedded JARs recursively without extracting or changing the source files."""
    found: list[dict[str, Any]] = []

    def walk(data: bytes, containing_path: str, depth: int) -> None:
        if depth > 8:
            return
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            return
        with archive:
            for name in archive.namelist():
                normalized = name.replace("\\", "/")
                lower_name = normalized.lower()
                if not lower_name.endswith(".jar"):
                    continue
                if not lower_name.startswith(("meta-inf/jars/", "meta-inf/jarjar/")):
                    continue
                try:
                    embedded = archive.read(name)
                except (KeyError, OSError, RuntimeError):
                    continue
                full_path = f"{containing_path}!/{normalized}"
                found.append(
                    {
                        "path": full_path,
                        "memberPath": normalized,
                        "fileName": PurePosixPath(normalized).name,
                        "sha256": sha256_bytes(embedded),
                        "officialProjectUrl": jar_homepage_from_bytes(embedded),
                        "containerArtifact": containing_path,
                    }
                )
                walk(embedded, full_path, depth + 1)

    for path in sorted(mods_directory.glob("*.jar"), key=lambda item: item.name.casefold()):
        try:
            walk(path.read_bytes(), f"mods/{path.name}", 0)
        except OSError:
            continue
    return found


def resolve_artifact_reference(
    reference: str,
    external_artifacts: dict[str, dict[str, Any]],
    embedded_by_full_path: dict[str, dict[str, Any]],
    embedded_by_member_path: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    normalized = reference.strip().replace("\\", "/")
    if "!/" in normalized and not normalized.startswith(("mods/", "/")):
        # The audit CSV records some Jar-in-Jar containers without the mods/ prefix.
        normalized = f"mods/{normalized}"
    lower = normalized.casefold()
    if lower in external_artifacts:
        artifact = external_artifacts[lower]
        return [
            {
                "componentType": "external-mod-jar",
                "path": artifact["file"],
                "sha256": artifact["sha256"],
                "sourceArtifact": artifact["file"],
            }
        ]

    if lower in embedded_by_full_path:
        embedded = embedded_by_full_path[lower]
        return [
            {
                "componentType": "jar-in-jar",
                "path": embedded["path"],
                "sha256": embedded["sha256"],
                "sourceArtifact": embedded["containerArtifact"],
            }
        ]

    if normalized.startswith("/"):
        member = normalized.lstrip("/").casefold()
        matches = [
            {
                "componentType": "jar-in-jar",
                "path": item["path"],
                "sha256": item["sha256"],
                "sourceArtifact": item["containerArtifact"],
            }
            for item in embedded_by_member_path.get(member, [])
        ]
        if not matches:
            # Some audit paths use META-INF/jarjar while the same named JAR is
            # physically stored under META-INF/jars. Resolve by the recorded
            # embedded filename only when the exact member path is absent.
            filename = PurePosixPath(normalized).name.casefold()
            matches = [
                {
                    "componentType": "jar-in-jar",
                    "path": item["path"],
                    "sha256": item["sha256"],
                    "sourceArtifact": item["containerArtifact"],
                }
                for item in embedded_by_full_path.values()
                if item["fileName"].casefold() == filename
            ]
        return matches

    return []


def dependency_is_required(relation: str) -> bool:
    return relation.strip().casefold().startswith("obrigat")


def unresolved_required_targets(
    runtime_ids: set[str], dependencies: list[dict[str, Any]]
) -> list[str]:
    environment_ids = set(ENVIRONMENT_IDS) | {"forge"}
    unresolved: set[str] = set()
    for dependency in dependencies:
        if not dependency["required"]:
            continue
        target = dependency["targetModId"]
        resolved_target = DEPENDENCY_ALIASES.get(target, target)
        if target not in runtime_ids and resolved_target not in runtime_ids and target not in environment_ids:
            unresolved.add(target)
    return sorted(unresolved)


def build_manifest(
    instance_root: Path,
    profile_path: Path,
    inventory_path: Path,
    dependencies_path: Path,
) -> dict[str, Any]:
    root = instance_root.resolve()
    mods_directory = root / "mods"
    if not mods_directory.is_dir():
        raise FileNotFoundError(f"No mods directory found at {mods_directory}")
    if not profile_path.is_absolute():
        profile_path = root / profile_path
    if not inventory_path.is_absolute():
        inventory_path = root / inventory_path
    if not dependencies_path.is_absolute():
        dependencies_path = root / dependencies_path

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    inventory_rows = read_semicolon_csv(inventory_path)
    dependency_rows = read_semicolon_csv(dependencies_path)

    profile_addons = [
        addon
        for addon in profile.get("installedAddons", [])
        if str(addon.get("packageType")) == "6"
    ]
    addons_by_filename: dict[str, list[dict[str, Any]]] = {}
    for addon in profile_addons:
        filename = addon.get("fileNameOnDisk")
        if filename:
            addons_by_filename.setdefault(str(filename).casefold(), []).append(addon)

    audit_by_filename: dict[str, dict[str, str]] = {}
    for row in inventory_rows:
        for reference in split_reported_values(row.get("artefatos_reportados")):
            if reference.startswith("mods/") and "!/" not in reference:
                audit_by_filename.setdefault(PurePosixPath(reference).name.casefold(), row)

    jar_paths = sorted(
        (path for path in mods_directory.iterdir() if path.is_file() and path.suffix.casefold() == ".jar"),
        key=lambda item: item.name.casefold(),
    )
    artifact_objects: list[dict[str, Any]] = []
    external_by_reference: dict[str, dict[str, Any]] = {}
    for path in jar_paths:
        filename = path.name
        candidates = addons_by_filename.get(filename.casefold(), [])
        audit_row = audit_by_filename.get(filename.casefold(), {})
        selected_addon = candidates[0] if len(candidates) == 1 else None
        resolution = "unique installed profile filename" if selected_addon else None
        candidate_pairs = {
            (as_positive_int(item.get("addonID")), as_positive_int((item.get("installedFile") or {}).get("id")))
            for item in candidates
        }
        if len(candidate_pairs) == 1 and candidates:
            selected_addon = candidates[0]
            resolution = "duplicate profile records share one project/file mapping"
        elif len(candidates) > 1:
            expected_fingerprint = as_nonnegative_int(audit_row.get("hash_curseforge"))
            matching: list[dict[str, Any]] = []
            for candidate in candidates:
                installed_candidate = candidate.get("installedFile") or {}
                candidate_fingerprint = as_nonnegative_int(installed_candidate.get("packageFingerprint"))
                candidate_sha1 = next(
                    (
                        str(item.get("value", "")).casefold()
                        for item in installed_candidate.get("hashes", [])
                        if item.get("type") == 1
                    ),
                    None,
                )
                audit_sha1 = audit_row.get("hash_modrinth", "").casefold()
                if (
                    expected_fingerprint is not None
                    and candidate_fingerprint == expected_fingerprint
                ) or (audit_sha1 and candidate_sha1 == audit_sha1):
                    matching.append(candidate)
            matching_pairs = {
                (as_positive_int(item.get("addonID")), as_positive_int((item.get("installedFile") or {}).get("id")))
                for item in matching
            }
            if len(matching_pairs) == 1 and matching:
                selected_addon = matching[0]
                resolution = "matched audit fingerprint/hash to installed CurseForge file metadata"

        addon = selected_addon
        installed_file = addon.get("installedFile") if addon else None
        installed_file = installed_file if isinstance(installed_file, dict) else {}
        project_id = as_positive_int(addon.get("addonID")) if addon else None
        file_id = as_positive_int(installed_file.get("id"))
        homepage = jar_homepage_from_path(path)
        project_url = official_url(addon.get("webSiteURL")) if addon else None
        if not project_url:
            project_url = homepage
        source: dict[str, Any] = {
            "platform": "CurseForge" if project_id and file_id else "unresolved",
            "projectID": project_id,
            "fileID": file_id,
            "officialProjectUrl": project_url,
            "officialDownloadUrl": official_url(installed_file.get("downloadUrl")),
            "metadataSource": "minecraftinstance.json" if addon else ("embedded mod metadata" if homepage else None),
            "metadataCandidateCount": len(candidates),
            "metadataResolution": resolution,
            "allowModDistribution": addon.get("allowModDistribution") if addon else None,
            "exportDisabledReason": addon.get("exportDisabledReason") if addon else None,
            "profileEnabled": addon.get("isEnabled") if addon else None,
            "distributionMethod": "CurseForge project/file reference" if project_id and file_id else "manual source or project release required",
        }
        if candidates and not addon:
            source["platform"] = "ambiguous CurseForge profile records"
            source["metadataSource"] = "minecraftinstance.json"
            source["candidateMappings"] = [
                {
                    "projectID": as_positive_int(candidate.get("addonID")),
                    "fileID": as_positive_int((candidate.get("installedFile") or {}).get("id")),
                    "officialProjectUrl": official_url(candidate.get("webSiteURL")),
                }
                for candidate in candidates
            ]
            source["distributionMethod"] = "manual metadata resolution required"
        local_source_path = None
        if filename.casefold() == "combatroll-hudfix-1.1.1.jar":
            patch_source = root / "patches" / "combatroll-hud-compat"
            if patch_source.is_dir():
                local_source_path = "patches/combatroll-hud-compat"
                source["platform"] = "Boundless project source"
                source["metadataSource"] = "project-owned source snapshot"
                source["distributionMethod"] = "project build/release required; not a CurseForge manifest entry"

        artifact = {
            "file": f"mods/{filename}",
            "fileName": filename,
            "sha256": sha256_file(path),
            "curseforge": source,
            "localSourcePath": local_source_path,
            "runtimeModIds": [],
        }
        artifact_objects.append(artifact)
        external_by_reference[artifact["file"].casefold()] = artifact

    embedded_objects = scan_embedded_archives(mods_directory)
    embedded_by_full_path = {item["path"].casefold(): item for item in embedded_objects}
    embedded_by_member_path: dict[str, list[dict[str, Any]]] = {}
    for item in embedded_objects:
        embedded_by_member_path.setdefault(item["memberPath"].casefold(), []).append(item)

    dependencies: list[dict[str, Any]] = []
    for row in dependency_rows:
        dependencies.append(
            {
                "declaringArtifact": row.get("artefato_que_declara", ""),
                "manifest": row.get("manifesto", ""),
                "sourceModId": row.get("mod_id_origem", ""),
                "targetModId": row.get("mod_id_alvo", ""),
                "relation": row.get("relacao", ""),
                "required": dependency_is_required(row.get("relacao", "")),
                "versionRange": row.get("faixa_versao_declarada", ""),
                "side": row.get("lado", ""),
                "declarationOrder": row.get("ordem", ""),
                "presentInRuntimeTable": row.get("presenca_na_lista_runtime", ""),
                "originalDeclaration": row.get("declaracao_original", ""),
            }
        )

    dependency_indices: dict[str, list[int]] = {}
    for index, dependency in enumerate(dependencies):
        dependency_indices.setdefault(dependency["sourceModId"], []).append(index)

    runtime_components: list[dict[str, Any]] = []
    used_embedded: dict[tuple[str, str], dict[str, Any]] = {}
    for row in inventory_rows:
        mod_id = row.get("mod_id", "")
        raw_references = split_reported_values(row.get("artefatos_reportados"))
        resolved_artifacts: list[dict[str, Any]] = []
        if mod_id.casefold() != "forge":
            for reference in raw_references:
                resolved = resolve_artifact_reference(
                    reference,
                    external_by_reference,
                    embedded_by_full_path,
                    embedded_by_member_path,
                )
                if not resolved:
                    resolved_artifacts.append(
                        {
                            "componentType": "unresolved-reference",
                            "path": reference,
                            "sha256": None,
                            "sourceArtifact": None,
                        }
                    )
                else:
                    resolved_artifacts.extend(resolved)

        direct_artifacts = [
            item for item in resolved_artifacts if item["componentType"] == "external-mod-jar"
        ]
        embedded_artifacts = [item for item in resolved_artifacts if item["componentType"] == "jar-in-jar"]
        if mod_id.casefold() == "forge":
            component_type = "loader-component"
        elif direct_artifacts:
            component_type = "external-mod"
        elif embedded_artifacts:
            component_type = "jar-in-jar-library"
        else:
            component_type = "unresolved"

        for item in direct_artifacts:
            artifact = external_by_reference.get(item["path"].casefold())
            if artifact and mod_id not in artifact["runtimeModIds"]:
                artifact["runtimeModIds"].append(mod_id)
        for item in embedded_artifacts:
            key = (item["path"], item["sha256"] or "")
            embedded = used_embedded.setdefault(
                key,
                {
                    "file": item["path"],
                    "fileName": PurePosixPath(item["path"].split("!/")[-1]).name,
                    "sha256": item["sha256"],
                    "containedIn": item["sourceArtifact"],
                    "officialProjectUrl": next(
                        (entry.get("officialProjectUrl") for entry in embedded_objects if entry["path"] == item["path"]),
                        None,
                    ),
                    "runtimeModIds": [],
                },
            )
            if mod_id not in embedded["runtimeModIds"]:
                embedded["runtimeModIds"].append(mod_id)

        runtime_components.append(
            {
                "id": mod_id,
                "name": row.get("nome_no_loader", ""),
                "versionsReported": split_reported_values(row.get("versoes_reportadas")),
                "componentType": component_type,
                "artifactReferences": raw_references,
                "artifacts": resolved_artifacts,
                "dependencyIndices": dependency_indices.get(mod_id, []),
            }
        )

    # The built-in Forge runtime ID is represented by the loader metadata, not a JAR in /mods.
    loader = profile.get("baseModLoader") or {}
    forge_version = str(loader.get("forgeVersion") or "")
    minecraft_version = str(profile.get("gameVersion") or "")
    forge_runtime = next((row for row in inventory_rows if row.get("mod_id") == "forge"), {})
    if forge_runtime.get("versoes_reportadas") and not forge_version:
        forge_version = split_reported_values(forge_runtime["versoes_reportadas"])[0]

    runtime_ids = {component["id"] for component in runtime_components}
    unresolved = unresolved_required_targets(runtime_ids, dependencies)
    identified_count = sum(
        bool(item["curseforge"].get("projectID") and item["curseforge"].get("fileID"))
        for item in artifact_objects
    )
    missing_cf_ids = [
        item["fileName"]
        for item in artifact_objects
        if not item["curseforge"].get("projectID") or not item["curseforge"].get("fileID")
    ]

    unreviewed_pack_paths: list[str] = []
    if any((root / "resourcepacks").glob("*.zip")):
        unreviewed_pack_paths.append("resourcepacks/")
    if any((root / "shaderpacks").glob("*.zip")):
        unreviewed_pack_paths.append("shaderpacks/")
    assets = {
        "unreviewedThirdPartyPackPaths": unreviewed_pack_paths,
        "redistributionTermsReviewed": False,
    }
    blockers = []
    if missing_cf_ids:
        blockers.append(
            f"{len(missing_cf_ids)} installed external JARs do not have verified CurseForge projectID/fileID metadata."
        )
    if unreviewed_pack_paths:
        blockers.append(
            "Third-party resourcepack/shaderpack redistribution terms have not been reviewed: "
            + ", ".join(unreviewed_pack_paths)
            + "."
        )
    if unresolved:
        blockers.append("One or more declared required dependency targets could not be resolved statically.")

    manifest = {
        "schemaVersion": 1,
        "project": {"name": str(profile.get("name") or "Boundless"), "baselineVersion": "0.1.0"},
        "platform": "CurseForge",
        "minecraft": {
            "version": minecraft_version,
            "sourceUrl": None,
        },
        "loader": {
            "id": "forge",
            "version": forge_version,
            "runtimeId": "forge",
            "downloadUrl": official_url(loader.get("downloadUrl")),
            "artifactFile": loader.get("filename"),
            "sha256": None,
            "acquisition": "CurseForge-managed Forge installer metadata",
        },
        "java": {
            "requiredMajorVersion": 17,
            "observedRuntimeVersion": "17.0.15",
            "source": "local crash report summarized by auditoria/AUDITORIA.md",
        },
        "externalArtifacts": artifact_objects,
        "runtimeComponents": runtime_components,
        "embeddedLibraries": sorted(used_embedded.values(), key=lambda item: item["file"].casefold()),
        "dependencies": dependencies,
        "dependencyResolution": {
            "environmentProvidedIds": sorted(set(ENVIRONMENT_IDS) | {"forge"}),
            "aliases": DEPENDENCY_ALIASES,
            "unresolvedRequiredTargets": unresolved,
        },
        "nonRedistributedAssets": assets,
        "reproducibility": {
            "status": "incomplete" if blockers else "metadata-complete",
            "curseforgeIdentifiedExternalJars": identified_count,
            "externalJarsWithoutCurseForgeIds": missing_cf_ids,
            "blockers": blockers,
        },
        "counts": {
            "externalJars": len(artifact_objects),
            "runtimeModIds": len(runtime_components),
            "dependencyDeclarations": len(dependencies),
            "curseforgeIdentifiedExternalJars": identified_count,
            "curseforgeProfileRecords": len(profile_addons),
            "uniqueCurseforgeProfileFilenames": len(addons_by_filename),
            "embeddedLibrariesReferencedByRuntimeInventory": len(used_embedded),
        },
        "inventorySource": {
            "runtimeModsCsv": "auditoria/inventario_mods.csv",
            "dependencyCsv": "auditoria/dependencias_mods.csv",
            "curseforgeProfileMetadata": "minecraftinstance.json (local-only; not committed)",
        },
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, default=ROOT)
    parser.add_argument("--profile", type=Path, default=Path("minecraftinstance.json"))
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--dependencies", type=Path, default=DEFAULT_DEPENDENCIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    root = args.instance_root.resolve()
    manifest = build_manifest(root, args.profile, args.inventory, args.dependencies)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = manifest["counts"]
    print(
        "Wrote {path}: {external} external JARs, {runtime} runtime IDs, "
        "{dependencies} dependency declarations, {identified} CurseForge file mappings.".format(
            path=output.relative_to(root) if output.is_relative_to(root) else output,
            external=counts["externalJars"],
            runtime=counts["runtimeModIds"],
            dependencies=counts["dependencyDeclarations"],
            identified=counts["curseforgeIdentifiedExternalJars"],
        )
    )
    if manifest["reproducibility"]["blockers"]:
        print("Reproduction status: incomplete")
        for blocker in manifest["reproducibility"]["blockers"]:
            print(f"- {blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
