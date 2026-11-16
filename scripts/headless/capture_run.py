#!/usr/bin/env python3
"""Preserve all useful logs and runtime outputs from one HeadlessMC pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_LOCK = json.loads((ROOT / "development" / "boundless-headless-test" / "runtime-lock.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_if_present(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args()

    destination = args.artifacts.resolve() / args.label
    destination.mkdir(parents=True, exist_ok=True)
    for relative in (
        "run/logs",
        "run/crash-reports",
        "run/headless-instance.json",
        "run/options.txt",
        "run/config/betterchunkloading.json",
        "HeadlessMC/logs",
    ):
        target = "headlessmc-logs" if relative == "HeadlessMC/logs" else relative.removeprefix("run/")
        copy_if_present(ROOT / relative, destination / target)

    mcrt_candidates = sorted((ROOT / "run" / "mods").glob("mc-runtime-test-*.jar"))
    hmc_jar = ROOT / "headlessmc.jar"
    dependency_state = {
        "headlessmc": {
            "version": RUNTIME_LOCK["headlessmc"]["version"],
            "expected_sha256": RUNTIME_LOCK["headlessmc"]["sha256"],
            "actual_sha256": sha256(hmc_jar) if hmc_jar.is_file() else None,
        },
        "mc_runtime_test": [
            {
                "file": jar.name,
                "version": RUNTIME_LOCK["mcRuntimeTest"]["version"],
                "expected_sha256": RUNTIME_LOCK["mcRuntimeTest"]["sha256"],
                "actual_sha256": sha256(jar),
            }
            for jar in mcrt_candidates
        ],
    }
    dependency_state["headlessmc"]["sha256_matches"] = (
        dependency_state["headlessmc"]["actual_sha256"] == dependency_state["headlessmc"]["expected_sha256"]
    )
    for dependency in dependency_state["mc_runtime_test"]:
        dependency["sha256_matches"] = dependency["actual_sha256"] == dependency["expected_sha256"]
    (destination / "runtime-dependencies.json").write_text(
        json.dumps(dependency_state, indent=2) + "\n", encoding="utf-8")

    state = {
        "label": args.label,
        "action_outcome": args.outcome,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (destination / "run-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Captured HeadlessMC outputs: {destination}")


if __name__ == "__main__":
    main()
