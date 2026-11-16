#!/usr/bin/env python3
"""Set only Better Chunk Loading's predictive loading switch for an A/B run."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "run" / "config" / "betterchunkloading.json"
PATTERN = re.compile(
    r'("enablePrediction"\s*:\s*\{(?:(?:\s*//[^\n]*\n)|(?:\s*/\*.*?\*/)|\s)*"enablePrediction"\s*:\s*)(true|false)',
    re.DOTALL,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enabled", choices=("true", "false", "current"), required=True)
    parser.add_argument("--condition", required=True)
    args = parser.parse_args()

    for directory in (
        ROOT / "run" / "saves",
        ROOT / "run" / "logs",
        ROOT / "run" / "crash-reports",
        ROOT / "HeadlessMC" / "logs",
    ):
        shutil.rmtree(directory, ignore_errors=True)
    (ROOT / "run" / "logs").mkdir(parents=True, exist_ok=True)

    if not CONFIG.is_file():
        raise SystemExit(f"Missing Better Chunk Loading config: {CONFIG}")
    text = CONFIG.read_text(encoding="utf-8")
    matches = list(PATTERN.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"Expected one enablePrediction setting, found {len(matches)}")
    current = matches[0].group(2)
    enabled = current if args.enabled == "current" else args.enabled
    if enabled != current:
        updated, count = PATTERN.subn(lambda match: match.group(1) + enabled, text)
        if count != 1:
            raise SystemExit(f"Expected one enablePrediction setting, found {count}")
        CONFIG.write_text(updated, encoding="utf-8")

    manifest_path = ROOT / "run" / "headless-instance.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["condition"] = args.condition
    manifest["better_chunk_loading_enable_prediction"] = enabled == "true"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared condition={args.condition}, Better Chunk Loading enablePrediction={enabled}")


if __name__ == "__main__":
    main()
