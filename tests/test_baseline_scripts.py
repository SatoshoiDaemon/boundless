from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.export_curseforge import make_curseforge_manifest, write_export_zip
from scripts.validate_manifest import compare_installed, validate_manifest


def sample_manifest() -> dict:
    data = b"fixture only; not a mod JAR"
    digest = hashlib.sha256(data).hexdigest()
    return {
        "schemaVersion": 1,
        "project": {"name": "Boundless", "baselineVersion": "0.1.0"},
        "platform": "CurseForge",
        "minecraft": {"version": "1.20.1", "sourceUrl": None},
        "loader": {"id": "forge", "version": "47.4.28", "runtimeId": "forge"},
        "externalArtifacts": [
            {
                "file": "mods/example.jar",
                "fileName": "example.jar",
                "sha256": digest,
                "curseforge": {
                    "projectID": 123,
                    "fileID": 456,
                    "officialProjectUrl": "https://www.curseforge.com/minecraft/mc-mods/example",
                    "officialDownloadUrl": "https://edge.forgecdn.net/files/example.jar",
                },
            }
        ],
        "runtimeComponents": [
            {
                "id": "example",
                "name": "Example Mod",
                "versionsReported": ["1.0.0"],
                "componentType": "external-mod",
                "artifactReferences": ["mods/example.jar"],
                "artifacts": [
                    {
                        "componentType": "external-mod-jar",
                        "path": "mods/example.jar",
                        "sha256": digest,
                        "sourceArtifact": "mods/example.jar",
                    }
                ],
                "dependencyIndices": [],
            }
        ],
        "embeddedLibraries": [],
        "dependencies": [],
        "dependencyResolution": {
            "environmentProvidedIds": ["forge", "java", "minecraft"],
            "aliases": {},
            "unresolvedRequiredTargets": [],
        },
        "nonRedistributedAssets": {
            "thirdPartyResourcePacksPresent": False,
            "thirdPartyShaderPacksPresent": False,
            "redistributionTermsReviewed": False,
        },
        "reproducibility": {
            "status": "metadata-complete",
            "curseforgeIdentifiedExternalJars": 1,
            "externalJarsWithoutCurseForgeIds": [],
            "blockers": [],
        },
        "counts": {
            "externalJars": 1,
            "runtimeModIds": 1,
            "dependencyDeclarations": 0,
            "curseforgeIdentifiedExternalJars": 1,
            "embeddedLibrariesReferencedByRuntimeInventory": 0,
        },
    }


class ValidateManifestTests(unittest.TestCase):
    def test_valid_manifest_passes(self) -> None:
        self.assertEqual(validate_manifest(sample_manifest(), require_baseline_counts=False), [])

    def test_unresolved_required_dependency_is_reported(self) -> None:
        data = sample_manifest()
        data["dependencies"] = [
            {
                "sourceModId": "example",
                "targetModId": "missing-library",
                "required": True,
            }
        ]
        data["counts"]["dependencyDeclarations"] = 1
        errors = validate_manifest(data, require_baseline_counts=False)
        self.assertTrue(any("missing-library" in error for error in errors))

    def test_manifest_count_mismatch_is_reported(self) -> None:
        data = sample_manifest()
        data["counts"]["externalJars"] = 2
        errors = validate_manifest(data, require_baseline_counts=False)
        self.assertTrue(any("externalJars" in error for error in errors))

    def test_incomplete_curseforge_mapping_cannot_be_exported(self) -> None:
        data = sample_manifest()
        artifact = data["externalArtifacts"][0]
        artifact["curseforge"]["projectID"] = None
        artifact["curseforge"]["fileID"] = None
        data["reproducibility"]["status"] = "incomplete"
        data["reproducibility"]["curseforgeIdentifiedExternalJars"] = 0
        data["reproducibility"]["externalJarsWithoutCurseForgeIds"] = ["example.jar"]
        data["counts"]["curseforgeIdentifiedExternalJars"] = 0
        with self.assertRaisesRegex(ValueError, "incomplete CurseForge export"):
            make_curseforge_manifest(data, "Boundless test", require_baseline_counts=False)

    def test_complete_export_uses_curseforge_manifest_shape(self) -> None:
        result = make_curseforge_manifest(
            sample_manifest(), "Boundless test", require_baseline_counts=False
        )
        self.assertEqual(result["manifestType"], "minecraftModpack")
        self.assertEqual(result["manifestVersion"], 1)
        self.assertEqual(result["minecraft"]["version"], "1.20.1")
        self.assertEqual(result["minecraft"]["modLoaders"][0]["id"], "forge-47.4.28")
        self.assertEqual(result["files"], [{"projectID": 123, "fileID": 456, "required": True}])
        self.assertEqual(result["overrides"], "overrides")

    def test_unreviewed_assets_block_complete_export(self) -> None:
        data = sample_manifest()
        data["reproducibility"]["status"] = "incomplete"
        data["reproducibility"]["blockers"] = ["Resourcepack terms need review."]
        with self.assertRaisesRegex(ValueError, "Resourcepack terms"):
            make_curseforge_manifest(data, "Boundless test", require_baseline_counts=False)

    def test_export_builds_overrides_and_excludes_runtime_binaries(self) -> None:
        data = sample_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "defaultconfigs").mkdir()
            (root / "kubejs").mkdir()
            (root / "datapacks").mkdir()
            (root / "mods").mkdir()
            (root / "resourcepacks").mkdir()
            (root / "shaderpacks").mkdir()
            (root / "saves").mkdir()
            (root / "logs").mkdir()
            (
                root / "config" / "pulse-trims" / "pack" / "assets" / "minecraft" / "shaders"
            ).mkdir(parents=True)
            (root / "config" / "pack.toml").write_text("enabled = true\n", encoding="utf-8")
            (root / "config" / "old.toml_backup1").write_text("backup\n", encoding="utf-8")
            (root / "config" / "pulse-trims" / "pack" / "pack.mcmeta").write_text(
                "third-party pack", encoding="utf-8"
            )
            (
                root
                / "config"
                / "pulse-trims"
                / "pack"
                / "assets"
                / "minecraft"
                / "shaders"
                / "third-party.fsh"
            ).write_text("third-party shader", encoding="utf-8")
            (root / "mods" / "example.jar").write_bytes(b"fixture only")
            (root / "resourcepacks" / "third-party.zip").write_bytes(b"fixture only")
            (root / "shaderpacks" / "third-party.zip").write_bytes(b"fixture only")
            (root / "saves" / "level.dat").write_bytes(b"fixture only")
            (root / "logs" / "latest.log").write_text("fixture only", encoding="utf-8")
            output = root / "out.zip"

            write_export_zip(
                manifest_data=data,
                author="Boundless test",
                instance_root=root,
                output_path=output,
                require_baseline_counts=False,
            )

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("overrides/", names)
                self.assertIn("overrides/config/pack.toml", names)
                self.assertNotIn("overrides/config/old.toml_backup1", names)
                self.assertIn("overrides/config/pulse-trims/pack/pack.mcmeta", names)
                self.assertIn(
                    "overrides/config/pulse-trims/pack/assets/minecraft/shaders/third-party.fsh",
                    names,
                )
                self.assertFalse(any(name.startswith("overrides/mods/") for name in names))
                self.assertFalse(any(name.startswith("overrides/resourcepacks/") for name in names))
                self.assertFalse(any(name.startswith("overrides/shaderpacks/") for name in names))
                self.assertFalse(any(name.startswith("overrides/saves/") for name in names))
                self.assertFalse(any(name.startswith("overrides/logs/") for name in names))

    def test_installed_comparison_detects_changes(self) -> None:
        data = sample_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mods = root / "mods"
            mods.mkdir()
            jar = mods / "example.jar"
            jar.write_bytes(b"fixture only; not a mod JAR")
            self.assertEqual(compare_installed(data, root), [])
            jar.write_bytes(b"changed fixture")
            self.assertTrue(any("SHA-256 mismatch" in error for error in compare_installed(data, root)))


if __name__ == "__main__":
    unittest.main()
