#!/usr/bin/env python3
"""Download locked HeadlessMC and install the pack's exact Forge version."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "development" / "boundless-headless-test" / "runtime-lock.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Boundless-Headless-CI"})
    with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual = sha256(temporary)
    if actual != expected_sha256:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"SHA-256 mismatch for {destination.name}: expected {expected_sha256}, got {actual}")
    temporary.replace(destination)
    print(f"Downloaded and verified {destination.name}: {actual}")


def main() -> None:
    launcher = os.environ.get("HMC_JAVA")
    game_java = os.environ.get("MC_JAVA_HOME")
    if not launcher or not Path(launcher).is_file():
        raise SystemExit("HMC_JAVA must point to the Java 25 launcher runtime")
    if not game_java or not (Path(game_java) / "bin" / "java").is_file():
        raise SystemExit("MC_JAVA_HOME must point to the Java 17 game runtime")

    mc_files = Path.home() / ".minecraft"
    hmc_dir = ROOT / "HeadlessMC"
    shutil.rmtree(hmc_dir, ignore_errors=True)
    hmc_dir.mkdir(parents=True, exist_ok=True)
    (hmc_dir / "config.properties").write_text(
        f"hmc.java.versions={game_java}\n"
        f"hmc.files.game={ROOT / 'run'}\n"
        "hmc.files.game-for-each-version=false\n"
        f"hmc.files.mc={mc_files}\n"
        "hmc.jline.enabled=false\n"
        "hmc.launcher.crash-report-watcher=true\n",
        encoding="utf-8",
    )

    hmc = ROOT / "headlessmc.jar"
    download(
        LOCK["headlessmc"]["downloadUrl"],
        hmc,
        LOCK["headlessmc"]["sha256"],
    )

    command = [
        launcher,
        "-jar",
        str(hmc),
        "version",
        "install",
        "forge",
        LOCK["minecraft"],
        LOCK["forge"],
    ]
    print(f"Installing pinned Minecraft {LOCK['minecraft']} / Forge {LOCK['forge']}")
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
