"""Create an official-format CurseForge modpack ZIP from the audited baseline."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from scripts.validate_manifest import DEFAULT_MANIFEST, ROOT, load_manifest, validate_manifest


OVERRIDE_DIRECTORIES = ("config", "defaultconfigs", "kubejs", "datapacks")
BACKUP_NAME = re.compile(r"(?:\.bak(?:[-.].*)?|\.backup(?:[-.].*)?|\.tmp|\.temp|\.old|\.orig|\.toml_backup\d*)$", re.I)


def make_curseforge_manifest(
    data: dict[str, Any], author: str, *, require_baseline_counts: bool = True
) -> dict[str, Any]:
    if not author.strip():
        raise ValueError("An explicit author is required for the CurseForge manifest.")
    validate_errors = validate_manifest(data, require_baseline_counts=require_baseline_counts)
    if validate_errors:
        raise ValueError("Canonical manifest validation failed: " + "; ".join(validate_errors))

    unresolved = data.get("reproducibility", {}).get("externalJarsWithoutCurseForgeIds", [])
    if unresolved:
        preview = ", ".join(unresolved[:5])
        extra = f" and {len(unresolved) - 5} more" if len(unresolved) > 5 else ""
        raise ValueError(
            f"Refusing an incomplete CurseForge export: {len(unresolved)} installed mod JARs "
            f"lack verified projectID/fileID metadata ({preview}{extra})."
        )
    blockers = data.get("reproducibility", {}).get("blockers", [])
    if blockers:
        raise ValueError("Refusing an incomplete CurseForge export: " + "; ".join(blockers))

    loader = data["loader"]
    if not loader.get("version"):
        raise ValueError("Forge version is missing from the canonical manifest.")
    files = [
        {
            "projectID": artifact["curseforge"]["projectID"],
            "fileID": artifact["curseforge"]["fileID"],
            "required": True,
        }
        for artifact in data["externalArtifacts"]
    ]
    unique_pairs = {(item["projectID"], item["fileID"]) for item in files}
    if len(unique_pairs) != len(files):
        raise ValueError("Duplicate CurseForge projectID/fileID entries found.")

    return {
        "minecraft": {
            "version": data["minecraft"]["version"],
            "modLoaders": [{"id": f"forge-{loader['version']}", "primary": True}],
        },
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": data["project"]["name"],
        "version": data["project"]["baselineVersion"],
        "author": author.strip(),
        "files": files,
        "overrides": "overrides",
    }


def is_backup(path: Path) -> bool:
    return bool(BACKUP_NAME.search(path.name))


def write_export_zip(
    *,
    manifest_data: dict[str, Any],
    author: str,
    instance_root: Path,
    output_path: Path,
    require_baseline_counts: bool = True,
) -> None:
    package_manifest = make_curseforge_manifest(
        manifest_data, author, require_baseline_counts=require_baseline_counts
    )
    root = instance_root.resolve()
    output = output_path.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists; choose another path or remove it explicitly: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(package_manifest, indent=2, ensure_ascii=False) + "\n",
        )
        archive.writestr("overrides/", b"")
        for directory in OVERRIDE_DIRECTORIES:
            source = root / directory
            if not source.is_dir():
                continue
            for path in sorted(source.rglob("*")):
                if not path.is_file() or is_backup(path):
                    continue
                if any(part in {".git", "__pycache__", "build", ".gradle"} for part in path.parts):
                    continue
                relative = path.relative_to(root).as_posix()
                archive.write(path, f"overrides/{relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--author", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/Boundless-0.1.0.zip"))
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output = args.output if args.output.is_absolute() else args.instance_root.resolve() / args.output
    try:
        write_export_zip(
            manifest_data=load_manifest(manifest_path),
            author=args.author,
            instance_root=args.instance_root,
            output_path=output,
        )
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(f"Created CurseForge package: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
