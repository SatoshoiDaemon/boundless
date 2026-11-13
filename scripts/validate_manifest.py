"""Validate the canonical dependency manifest and compare it with installed JARs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.build_manifest import DEPENDENCY_ALIASES, ENVIRONMENT_IDS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("manifests/dependencies.json")
BASELINE_COUNTS = {
    "externalJars": 425,
    "runtimeModIds": 491,
    "dependencyDeclarations": 1160,
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BAD_RELATIVE_PARTS = {".."}


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    parts = value.replace("\\", "/").split("/")
    return not any(part in BAD_RELATIVE_PARTS for part in parts)


def validate_manifest(
    manifest: dict[str, Any], *, require_baseline_counts: bool = True
) -> list[str]:
    errors: list[str] = []
    if manifest.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if manifest.get("platform") != "CurseForge":
        errors.append("platform must be CurseForge")

    artifacts = manifest.get("externalArtifacts")
    runtime_components = manifest.get("runtimeComponents")
    dependencies = manifest.get("dependencies")
    embedded = manifest.get("embeddedLibraries")
    counts = manifest.get("counts")
    if not isinstance(artifacts, list):
        errors.append("externalArtifacts must be a list")
        artifacts = []
    if not isinstance(runtime_components, list):
        errors.append("runtimeComponents must be a list")
        runtime_components = []
    if not isinstance(dependencies, list):
        errors.append("dependencies must be a list")
        dependencies = []
    if not isinstance(embedded, list):
        errors.append("embeddedLibraries must be a list")
        embedded = []
    if not isinstance(counts, dict):
        errors.append("counts must be an object")
        counts = {}

    if counts.get("externalJars") != len(artifacts):
        errors.append("counts.externalJars does not match externalArtifacts")
    if counts.get("runtimeModIds") != len(runtime_components):
        errors.append("counts.runtimeModIds does not match runtimeComponents")
    if counts.get("dependencyDeclarations") != len(dependencies):
        errors.append("counts.dependencyDeclarations does not match dependencies")
    if counts.get("embeddedLibrariesReferencedByRuntimeInventory") != len(embedded):
        errors.append("embedded library count does not match embeddedLibraries")

    if require_baseline_counts:
        for key, expected in BASELINE_COUNTS.items():
            if counts.get(key) != expected:
                errors.append(f"baseline count {key} must be {expected}; found {counts.get(key)!r}")

    artifact_by_path: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("each external artifact must be an object")
            continue
        path = artifact.get("file")
        if not valid_relative_path(path) or not str(path).startswith("mods/"):
            errors.append(f"invalid external artifact path: {path!r}")
        elif str(path).casefold() in artifact_by_path:
            errors.append(f"duplicate external artifact path: {path}")
        else:
            artifact_by_path[str(path).casefold()] = artifact
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"invalid SHA-256 for {path!r}")
        curseforge = artifact.get("curseforge")
        if not isinstance(curseforge, dict):
            errors.append(f"missing CurseForge/acquisition metadata for {path!r}")
            continue
        project_id = curseforge.get("projectID")
        file_id = curseforge.get("fileID")
        if (project_id is None) != (file_id is None):
            errors.append(f"projectID and fileID must both be present or both be null for {path!r}")
        for key in ("officialProjectUrl", "officialDownloadUrl"):
            url = curseforge.get(key)
            if url is not None and not (isinstance(url, str) and url.startswith(("https://", "http://"))):
                errors.append(f"invalid {key} for {path!r}")

    runtime_ids: set[str] = set()
    for component in runtime_components:
        if not isinstance(component, dict):
            errors.append("each runtime component must be an object")
            continue
        mod_id = component.get("id")
        if not isinstance(mod_id, str) or not mod_id:
            errors.append("runtime component has no mod ID")
            continue
        if mod_id in runtime_ids:
            errors.append(f"duplicate runtime mod ID: {mod_id}")
        runtime_ids.add(mod_id)
        if component.get("componentType") not in {
            "external-mod",
            "jar-in-jar-library",
            "loader-component",
            "unresolved",
        }:
            errors.append(f"invalid componentType for runtime ID {mod_id}")
        for index in component.get("dependencyIndices", []):
            if not isinstance(index, int) or index < 0 or index >= len(dependencies):
                errors.append(f"invalid dependency index for runtime ID {mod_id}")
                continue
            if dependencies[index].get("sourceModId") != mod_id:
                errors.append(f"dependency index {index} has the wrong source mod ID for {mod_id}")
        for reference in component.get("artifacts", []):
            if not isinstance(reference, dict):
                errors.append(f"invalid artifact reference for runtime ID {mod_id}")
                continue
            if not valid_relative_path(reference.get("path")):
                errors.append(f"invalid runtime artifact path for {mod_id}: {reference.get('path')!r}")
            digest = reference.get("sha256")
            if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
                errors.append(f"invalid runtime artifact SHA-256 for {mod_id}")

    resolution = manifest.get("dependencyResolution", {})
    environment_ids = set(resolution.get("environmentProvidedIds", [])) | set(ENVIRONMENT_IDS) | {"forge"}
    aliases = dict(DEPENDENCY_ALIASES)
    aliases.update(resolution.get("aliases", {}))
    unresolved_targets: set[str] = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            errors.append("each dependency declaration must be an object")
            continue
        if not dependency.get("required"):
            continue
        target = dependency.get("targetModId", "")
        resolved = aliases.get(target, target)
        if target not in runtime_ids and resolved not in runtime_ids and target not in environment_ids:
            unresolved_targets.add(target)
    if unresolved_targets:
        errors.append("unresolved required dependency targets: " + ", ".join(sorted(unresolved_targets)))

    declared_unresolved = set(resolution.get("unresolvedRequiredTargets", []))
    if declared_unresolved != unresolved_targets:
        errors.append("dependencyResolution.unresolvedRequiredTargets does not match the graph check")

    for embedded_library in embedded:
        if not isinstance(embedded_library, dict):
            errors.append("each embedded library must be an object")
            continue
        if not valid_relative_path(embedded_library.get("file")):
            errors.append(f"invalid embedded library path: {embedded_library.get('file')!r}")
        digest = embedded_library.get("sha256")
        if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
            errors.append(f"invalid embedded library SHA-256: {embedded_library.get('file')!r}")

    missing_cf_ids = [
        artifact["fileName"]
        for artifact in artifacts
        if not artifact.get("curseforge", {}).get("projectID")
        or not artifact.get("curseforge", {}).get("fileID")
    ]
    reproduction = manifest.get("reproducibility", {})
    declared_missing = reproduction.get("externalJarsWithoutCurseForgeIds", [])
    if sorted(missing_cf_ids) != sorted(declared_missing):
        errors.append("reproducibility.externalJarsWithoutCurseForgeIds does not match artifact metadata")
    if reproduction.get("curseforgeIdentifiedExternalJars") != len(artifacts) - len(missing_cf_ids):
        errors.append("reproducibility CurseForge file mapping count does not match artifact metadata")
    if reproduction.get("status") not in {"incomplete", "metadata-complete"}:
        errors.append("reproducibility.status must be incomplete or metadata-complete")

    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_installed(manifest: dict[str, Any], instance_root: Path) -> list[str]:
    mods_directory = instance_root / "mods"
    if not mods_directory.is_dir():
        return [f"installed mods directory does not exist: {mods_directory}"]

    expected = {
        artifact["file"].casefold(): artifact
        for artifact in manifest.get("externalArtifacts", [])
        if isinstance(artifact, dict) and isinstance(artifact.get("file"), str)
    }
    installed_paths = {
        f"mods/{path.name}".casefold(): path
        for path in mods_directory.iterdir()
        if path.is_file() and path.suffix.casefold() == ".jar"
    }
    errors: list[str] = []
    for path in sorted(expected.keys() - installed_paths.keys()):
        errors.append(f"missing installed JAR: {expected[path]['file']}")
    for path in sorted(installed_paths.keys() - expected.keys()):
        errors.append(f"additional installed JAR: mods/{installed_paths[path].name}")
    for key in sorted(expected.keys() & installed_paths.keys()):
        installed_path = installed_paths[key]
        actual_hash = sha256_file(installed_path)
        expected_hash = expected[key].get("sha256")
        if actual_hash != expected_hash:
            errors.append(f"changed installed JAR: {expected[key]['file']} (SHA-256 mismatch)")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static", action="store_true", help="validate metadata without installed binaries")
    mode.add_argument("--compare-installed", action="store_true", help="also compare installed mod JARs")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--instance-root", type=Path, default=ROOT)
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    manifest = load_manifest(manifest_path)
    errors = validate_manifest(manifest)
    if args.compare_installed:
        errors.extend(compare_installed(manifest, args.instance_root.resolve()))
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    counts = manifest["counts"]
    print(
        "Manifest valid: {external} external JARs, {runtime} runtime IDs, "
        "{dependencies} dependency declarations.".format(
            external=counts["externalJars"],
            runtime=counts["runtimeModIds"],
            dependencies=counts["dependencyDeclarations"],
        )
    )
    if args.compare_installed:
        print("Installed JAR names and SHA-256 hashes match the manifest.")
    print(f"Reproduction status: {manifest['reproducibility']['status']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
