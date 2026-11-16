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
        "mcRuntimeTest": "headlesshq/mc-runtime-test",
        "uploadArtifact": "actions/upload-artifact",
    }
    errors: list[str] = []
    for key, action in action_names.items():
        pin = f"{action}@{LOCK['actions'][key]}"
        if pin not in workflow:
            errors.append(f"workflow action pin does not match runtime-lock.json: {pin}")

    for locked_value in (
        LOCK["minecraft"],
        LOCK["forge"],
        str(LOCK["javaMajor"]),
        LOCK["headlessmc"]["version"],
        LOCK["mcRuntimeTest"]["version"],
    ):
        if f'"{locked_value}"' not in workflow and f"={locked_value} " not in workflow:
            errors.append(f"workflow does not reference locked runtime value {locked_value}")

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
