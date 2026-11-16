#!/usr/bin/env python3
"""Ensure the workflow and build wrappers match the checked-in runtime lock."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "development" / "boundless-headless-test" / "runtime-lock.json").read_text(encoding="utf-8"))


def main() -> None:
    workflow = (ROOT / ".github" / "workflows" / "headless-mc.yml").read_text(encoding="utf-8")
    action_names = {
        "checkout": "actions/checkout",
        "setupPython": "actions/setup-python",
        "setupJava": "actions/setup-java",
        "cache": "actions/cache",
        "uploadArtifact": "actions/upload-artifact",
    }
    errors: list[str] = []
    for key, action in action_names.items():
        pin = f"{action}@{LOCK['actions'][key]}"
        if pin not in workflow:
            errors.append(f"workflow action pin does not match runtime-lock.json: {pin}")

    download_mcrt = ROOT / "scripts" / "headless" / "download_mcrt.py"
    install_runtime = ROOT / "scripts" / "headless" / "install_runtime.py"
    launch_client = ROOT / "scripts" / "headless" / "run_client.py"
    for script in (download_mcrt, install_runtime, launch_client):
        if not script.is_file():
            errors.append(f"runtime script is missing: {script.relative_to(ROOT)}")
    if download_mcrt.is_file():
        content = download_mcrt.read_text(encoding="utf-8")
        for field in ('LOCK["mcRuntimeTest"]', '["downloadUrl"]', '["sha256"]', '["file"]'):
            if field not in content:
                errors.append(f"MC-Runtime-Test downloader does not use the locked field {field}")
    if install_runtime.is_file():
        content = install_runtime.read_text(encoding="utf-8")
        for field in ('LOCK["headlessmc"]', 'LOCK["minecraft"]', 'LOCK["forge"]'):
            if field not in content:
                errors.append(f"HeadlessMC runtime installer does not use the locked field {field}")
    if launch_client.is_file():
        content = launch_client.read_text(encoding="utf-8")
        for field in ('LOCK["mcRuntimeTest"]', 'LOCK["minecraft"]', 'LOCK["forge"]'):
            if field not in content:
                errors.append(f"HeadlessMC launcher does not use the locked field {field}")
    if "scripts/headless/install_runtime.py" not in workflow or "scripts/headless/download_mcrt.py" not in workflow:
        errors.append("workflow does not download and install the version-locked HeadlessMC runtime")
    if "scripts/headless/run_client.py" not in workflow:
        errors.append("workflow does not launch tests through the version-locked HeadlessMC runner")
    if "headlesshq/mc-runtime-test@" in workflow:
        errors.append("workflow must use the exact locked MC-Runtime-Test jar, not the action's wildcard download")

    for project in ("boundless-compat", "boundless-fix", "boundless-tweaks", "boundless-headless-test"):
        build_file = ROOT / "development" / project / "build.gradle"
        if not build_file.is_file():
            continue
        if f"version '{LOCK['forgeGradle']}'" not in build_file.read_text(encoding="utf-8"):
            errors.append(f"{project} does not pin ForgeGradle {LOCK['forgeGradle']}")

        properties = ROOT / "development" / project / "gradle.properties"
        if properties.is_file():
            content = properties.read_text(encoding="utf-8")
            if f"minecraft_version={LOCK['minecraft']}" not in content:
                errors.append(f"{project} does not target Minecraft {LOCK['minecraft']}")
            if f"forge_version={LOCK['forge']}" not in content:
                errors.append(f"{project} does not target Forge {LOCK['forge']}")

    wrapper_digest = LOCK["gradle"]["distributionSha256"]
    for project in ("boundless-compat", "boundless-fix", "boundless-tweaks"):
        properties = ROOT / "development" / project / "gradle" / "wrapper" / "gradle-wrapper.properties"
        content = properties.read_text(encoding="utf-8")
        if f"gradle-{LOCK['gradle']['version']}-bin.zip" not in content:
            errors.append(f"{project} wrapper does not pin Gradle {LOCK['gradle']['version']}")
        if f"distributionSha256Sum={wrapper_digest}" not in content:
            errors.append(f"{project} wrapper distribution checksum does not match runtime-lock.json")

    if errors:
        raise SystemExit("Runtime lock validation failed:\n- " + "\n- ".join(errors))
    print("Runtime lock, workflow action pins, ForgeGradle, and Gradle wrapper checksums match.")


if __name__ == "__main__":
    main()
