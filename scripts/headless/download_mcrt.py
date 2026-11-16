#!/usr/bin/env python3
"""Download and verify the exact MC-Runtime-Test jar in the runtime lock."""

from __future__ import annotations

import hashlib
import json
import shutil
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


def main() -> None:
    runtime = LOCK["mcRuntimeTest"]
    destination = ROOT / "run" / "mods" / runtime["file"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(runtime["downloadUrl"], headers={"User-Agent": "Boundless-Headless-CI"})
    with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual = sha256(temporary)
    if actual != runtime["sha256"]:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"MC-Runtime-Test SHA-256 mismatch: expected {runtime['sha256']}, got {actual}")
    temporary.replace(destination)
    print(f"Downloaded and verified {destination.name}: {actual}")


if __name__ == "__main__":
    main()
