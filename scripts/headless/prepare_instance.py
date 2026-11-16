#!/usr/bin/env python3
"""Build a clean, versioned HeadlessMC game directory for one test tier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_LOCK = json.loads((ROOT / "development" / "boundless-headless-test" / "runtime-lock.json").read_text(encoding="utf-8"))
RUN = ROOT / "run"
CUSTOM_MODS = (
    "boundless-compat",
    "boundless-fix",
    "boundless-tweaks",
)
HEADLESS_TEST_MOD = "boundless-headless-test"
FULL_PACK_LEVELS = {"full-modpack", "world"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_jars(project: str) -> list[Path]:
    libs = ROOT / "development" / project / "build" / "libs"
    if not libs.is_dir():
        raise RuntimeError(f"Build output is missing: {libs}")
    jars = sorted(
        path for path in libs.glob("*.jar")
        if not any(part in path.name.lower() for part in ("sources", "javadoc", "dev"))
    )
    if len(jars) != 1:
        raise RuntimeError(f"Expected one distributable jar in {libs}, found {len(jars)}")
    return jars


def copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", required=True,
                        choices=("bootstrap", "forge", "boundless-mods", "full-modpack", "world"))
    parser.add_argument("--target-ref", default="")
    parser.add_argument("--commit", default="")
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args()

    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    if RUN.exists():
        shutil.rmtree(RUN)
    (RUN / "mods").mkdir(parents=True)
    (RUN / "logs").mkdir(parents=True)

    copied_mods: list[Path] = []
    if args.level in FULL_PACK_LEVELS:
        source_mods = ROOT / "mods"
        pack_jars = sorted(source_mods.glob("*.jar"))
        if len(pack_jars) < 400:
            raise RuntimeError(f"Full pack checkout is incomplete: expected at least 400 jars, found {len(pack_jars)}")
        for jar in pack_jars:
            with jar.open("rb") as source:
                data = source.read(128)
            if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise RuntimeError(f"Git LFS object was not hydrated: {jar}")
            shutil.copy2(jar, RUN / "mods" / jar.name)
            copied_mods.append(jar)

        for directory in ("config", "defaultconfigs", "kubejs", "resourcepacks", "shaderpacks"):
            copy_tree(ROOT / directory, RUN / directory)

    if args.level in {"boundless-mods", "full-modpack", "world"}:
        for project in CUSTOM_MODS:
            for jar in build_jars(project):
                shutil.copy2(jar, RUN / "mods" / jar.name)
                copied_mods.append(jar)

    if args.level in {"forge", "boundless-mods", "full-modpack", "world"}:
        for jar in build_jars(HEADLESS_TEST_MOD):
            shutil.copy2(jar, RUN / "mods" / jar.name)
            copied_mods.append(jar)

    (RUN / "options.txt").write_text(
        "onboardAccessibility:false\n"
        "pauseOnLostFocus:false\n"
        "narrator:0\n"
        "renderDistance:8\n"
        "simulationDistance:6\n"
        "autoJump:true\n"
        "enableVsync:false\n",
        encoding="utf-8",
    )

    if args.level == "world":
        bcl_config = RUN / "config" / "betterchunkloading.json"
        if not bcl_config.is_file():
            raise RuntimeError("The full pack config/betterchunkloading.json was not staged")

    manifest = {
        "target_ref": args.target_ref,
        "commit": args.commit,
        "test_level": args.level,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": os.environ.get("RUNNER_NAME", "ubuntu-latest"),
        "os": os.environ.get("RUNNER_OS", "Linux"),
        "minecraft": RUNTIME_LOCK["minecraft"],
        "forge_expected": RUNTIME_LOCK["forge"],
        "java": str(RUNTIME_LOCK["javaMajor"]),
        "headlessmc": RUNTIME_LOCK["headlessmc"]["version"],
        "mc_runtime_test": RUNTIME_LOCK["mcRuntimeTest"]["version"],
        "mod_count": len(list((RUN / "mods").glob("*.jar"))),
        "mods": [
            {"name": path.name, "sha256": sha256(RUN / "mods" / path.name)}
            for path in sorted(copied_mods, key=lambda item: item.name.lower())
        ],
        "world_options": {
            "render_distance": 8,
            "simulation_distance": 6,
            "fixed_seed": "4242424242" if args.level == "world" else None,
            "movement_ticks": 1200 if args.level == "world" else None,
        },
    }
    (RUN / "headless-instance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (artifacts / "instance-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"test_level": args.level, "staged_mod_count": manifest["mod_count"],
                      "artifact_manifest": str(artifacts / "instance-manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
