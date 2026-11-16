#!/usr/bin/env python3
"""Fail after artifacts are published if a selected check or experiment failed."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_LOCK = json.loads((ROOT / "development" / "boundless-headless-test" / "runtime-lock.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", required=True)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--action-status", action="append", default=[])
    parser.add_argument("--experiment", default="none")
    args = parser.parse_args()

    failures = [status for status in args.action_status if status and status not in {"success", "skipped"}]

    def check_runtime_dependencies(label: str) -> None:
        path = args.artifacts / label / "runtime-dependencies.json"
        if not path.is_file():
            failures.append(f"{label}: runtime dependency hash report missing")
            return
        state = json.loads(path.read_text(encoding="utf-8"))
        if not state.get("headlessmc", {}).get("sha256_matches"):
            failures.append(f"{label}: HeadlessMC checksum is missing or does not match the lock file")
        mcrt = state.get("mc_runtime_test", [])
        expected_mcrt = RUNTIME_LOCK["mcRuntimeTest"]["file"]
        pinned_mcrt = next((item for item in mcrt if item.get("file") == expected_mcrt), None)
        if not state.get("expected_mc_runtime_test_present") or not pinned_mcrt or not pinned_mcrt.get("sha256_matches"):
            failures.append(f"{label}: MC-Runtime-Test checksum is missing or does not match the lock file")

    expected_runtime_labels = []
    if args.level == "bootstrap":
        expected_runtime_labels = ["bootstrap"]
    elif args.level == "world":
        if args.experiment == "ab":
            expected_runtime_labels = ["prediction-on", "prediction-off"]
        elif args.experiment == "on":
            expected_runtime_labels = ["prediction-on"]
        elif args.experiment == "off":
            expected_runtime_labels = ["prediction-off"]
        else:
            expected_runtime_labels = ["world"]
    else:
        expected_runtime_labels = ["runtime"]
    for runtime_label in expected_runtime_labels:
        check_runtime_dependencies(runtime_label)

    if args.level != "bootstrap":
        smoke_path = args.artifacts / "runtime" / "logs" / "headless-smoke-report.json"
        if args.level == "world":
            smoke_path = None
        if smoke_path is not None:
            if not smoke_path.is_file():
                failures.append("Forge GameTest smoke report missing")
            else:
                smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
                if smoke.get("forge_version") != RUNTIME_LOCK["forge"]:
                    failures.append(f"expected Forge {RUNTIME_LOCK['forge']}, found {smoke.get('forge_version')}")
                if args.level in {"boundless-mods", "full-modpack"}:
                    expected_mods = {"boundlesscompat", "boundlessfix", "boundlesstweaks"}
                    loaded = set(smoke.get("boundless_mods_loaded", []))
                    if not expected_mods.issubset(loaded):
                        failures.append("not all Boundless development mods were loaded")
                if args.level == "full-modpack":
                    if smoke.get("loaded_mod_count", 0) < 400:
                        failures.append("full pack loaded fewer than 400 mods")
                    if not smoke.get("better_chunk_loading_loaded"):
                        failures.append("Better Chunk Loading did not load in the full pack")
    if args.level == "world":
        expected = []
        if args.experiment == "ab":
            expected = ["prediction-on", "prediction-off"]
        elif args.experiment == "on":
            expected = ["prediction-on"]
        elif args.experiment == "off":
            expected = ["prediction-off"]
        else:
            expected = ["world"]

        reports = []
        for label in expected:
            report = args.artifacts / label / "logs" / "headless-world-report.json"
            if not report.is_file():
                failures.append(f"{label}: world metrics report missing")
                continue
            data = json.loads(report.read_text(encoding="utf-8"))
            reports.append((label, data))
            if not data.get("seed_field_applied"):
                failures.append(f"{label}: fixed seed was not applied")
            if data.get("seed") != data.get("expected_seed"):
                failures.append(f"{label}: generated world seed did not match the requested seed")
            if not data.get("better_chunk_loading_loaded"):
                failures.append(f"{label}: Better Chunk Loading did not load")
            if args.experiment == "none":
                config_path = args.artifacts / label / "config" / "betterchunkloading.json"
                try:
                    config_text = config_path.read_text(encoding="utf-8")
                    config_match = re.search(
                        r'"enablePrediction"\s*:\s*\{(?:(?:\s*//[^\n]*\n)|(?:\s*/\*.*?\*/)|\s)*"enablePrediction"\s*:\s*(true|false)',
                        config_text,
                        re.DOTALL,
                    )
                except FileNotFoundError:
                    config_match = None
                if config_match is None:
                    failures.append(f"{label}: captured Better Chunk Loading config is missing or unreadable")
                elif data.get("enable_prediction") is not (config_match.group(1) == "true"):
                    failures.append(f"{label}: measured Better Chunk Loading setting differs from the captured config")
            if data.get("loaded_mod_count", 0) < 400:
                failures.append(f"{label}: full pack loaded fewer than 400 mods")
            if not data.get("forge_version") == RUNTIME_LOCK["forge"]:
                failures.append(f"{label}: expected Forge {RUNTIME_LOCK['forge']}, found {data.get('forge_version')}")
            if data.get("player_travel_blocks", 0) < 8:
                failures.append(f"{label}: player movement workload traveled fewer than 8 blocks")
            minimum_tick_samples = max(100, int(data.get("requested_ticks", 1200) * 0.90))
            if data.get("server_ticks_sampled", 0) < minimum_tick_samples:
                failures.append(f"{label}: fewer than {minimum_tick_samples} server tick samples were recorded")
            smoke_path = args.artifacts / label / "logs" / "headless-smoke-report.json"
            if not smoke_path.is_file():
                failures.append(f"{label}: Forge smoke report missing")
            else:
                smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
                if smoke.get("forge_version") != RUNTIME_LOCK["forge"]:
                    failures.append(f"{label}: expected Forge {RUNTIME_LOCK['forge']}, found {smoke.get('forge_version')}")
                expected_mods = {"boundlesscompat", "boundlessfix", "boundlesstweaks"}
                if not expected_mods.issubset(set(smoke.get("boundless_mods_loaded", []))):
                    failures.append(f"{label}: one or more Boundless development mods did not load")
                if smoke.get("loaded_mod_count", 0) < 400:
                    failures.append(f"{label}: full pack loaded fewer than 400 mods")
            expected_prediction = {"on": True, "off": False}.get(args.experiment)
            if expected_prediction is not None and data.get("enable_prediction") is not expected_prediction:
                failures.append(f"{label}: Better Chunk Loading setting did not match experiment '{args.experiment}'")
        if args.experiment == "ab" and len(reports) == 2:
            on = next((data for label, data in reports if label == "prediction-on"), {})
            off = next((data for label, data in reports if label == "prediction-off"), {})
            if on.get("seed") != off.get("seed"):
                failures.append("A/B passes did not use the same actual world seed")
            if on.get("enable_prediction") is not True or off.get("enable_prediction") is not False:
                failures.append("A/B passes did not record the requested enablePrediction values")

    if failures:
        print("Headless run failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)
    print("All selected HeadlessMC checks passed.")


if __name__ == "__main__":
    main()
