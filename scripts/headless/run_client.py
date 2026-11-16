#!/usr/bin/env python3
"""Run a pinned HeadlessMC Minecraft client under Xvfb for one test condition."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "development" / "boundless-headless-test" / "runtime-lock.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", required=True, choices=("bootstrap", "forge", "boundless-mods", "full-modpack", "world"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--seed", default="4242424242")
    parser.add_argument("--ticks", type=int, default=1200)
    parser.add_argument("--condition", default="runtime")
    args = parser.parse_args()

    hmc_java = os.environ.get("HMC_JAVA")
    if not hmc_java or not Path(hmc_java).is_file():
        raise SystemExit("HMC_JAVA must point to the Java 25 HeadlessMC launcher")
    mc_runtime = ROOT / "run" / "mods" / LOCK["mcRuntimeTest"]["file"]
    if not mc_runtime.is_file():
        raise SystemExit(f"Pinned MC-Runtime-Test jar is missing: {mc_runtime}")

    destination = args.artifacts.resolve() / args.label
    destination.mkdir(parents=True, exist_ok=True)
    (ROOT / "run" / "logs").mkdir(parents=True, exist_ok=True)
    (ROOT / "run" / "crash-reports").mkdir(parents=True, exist_ok=True)

    memory = "-Xms512m -Xmx3G" if args.level == "bootstrap" else "-Xms1G -Xmx5G"
    properties = [
        "-Djava.awt.headless=true",
        memory,
    ]
    if args.level != "bootstrap":
        properties.extend([
            "-Dforge.enabledGameTestNamespaces=boundless_headless_test",
            "-DMcRuntimeGameTestMinExpectedGameTests=2",
            f"-Dboundless.headless.testLevel={args.level}",
            f"-Dboundless.headless.requireBoundlessMods={str(args.level in {'boundless-mods', 'full-modpack', 'world'}).lower()}",
            f"-Dboundless.headless.requireBcl={str(args.level in {'full-modpack', 'world'}).lower()}",
            f"-Dboundless.headless.expectedForge={LOCK['forge']}",
        ])
    if args.level == "world":
        properties.extend([
            "-Dboundless.headless.worldWorkload=true",
            f"-Dboundless.headless.seed={args.seed}",
            f"-Dboundless.headless.ticks={args.ticks}",
            f"-Dboundless.headless.condition={args.condition}",
        ])

    gc_log = destination / "gc.log"
    jfr = destination / "minecraft.jfr"
    properties.extend([
        f"-Xlog:gc*:file={gc_log}:time,uptime,level,tags",
        f"-XX:StartFlightRecording=filename={jfr},settings=profile,dumponexit=true",
    ])
    jvm_args = " ".join(properties)
    command = [
        "xvfb-run",
        "-a",
        "-s",
        "-screen 0 1920x1080x24 +extension GLX +render -noreset",
        hmc_java,
        "-Dhmc.xvfb.check=true",
        "-jar",
        str(ROOT / "headlessmc.jar"),
        "launch",
        "--offline",
        "--no-backup",
        "--jvm",
        jvm_args,
        "forge",
        LOCK["minecraft"],
        LOCK["forge"],
    ]
    (destination / "launcher-command.json").write_text(
        json.dumps({"working_directory": str(ROOT), "command": command, "forge_version": LOCK["forge"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Starting HeadlessMC for level={args.level}, pass={args.label}, Forge={LOCK['forge']}")
    sys.exit(subprocess.run(command, cwd=ROOT).returncode)


if __name__ == "__main__":
    main()
