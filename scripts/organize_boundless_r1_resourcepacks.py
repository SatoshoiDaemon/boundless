from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCEPACKS = ROOT / "resourcepacks"
AUDIT = ROOT / "auditoria" / "rodada-1"
OPTIONS = ROOT / "options.txt"
COMPAT_NAME = "Boundless R1 Resource Compatibility.zip"

# The order is lowest to highest priority. Broad themes/textures go first;
# focused item, GUI, and animation layers go later.
PRIORITY = [
    "Soft-Weather",
    "cubic-sun-moon",
    "Enhanced Audio Ambience",
    "Enhanced Audio r7",
    "Alternative Rain Sounds 1.21-1.21.1",
    "Cataclysmic_tunes",
    "Default-Dark-Mode",
    "Vanilla Experience+",
    "Farcr's Re-Crafted",
    "Better_End_Portal_Frame",
    "Lanterns with Candles",
    "Just Fancy Torches",
    "Fancy Crops",
    "Leaves Experience+",
    "Glowing Trim Elytra",
    "Armors.zip",
    "Cataclysm Reimagined v1.3.5 for NeoForge",
    "Chests",
    "Armorstands",
    "EnderEyes",
    "Better Zombies",
    "FreshAnimations_v1.11.2_1.20",
    "FA-All_Extensions",
    "FA-Details",
    "FA-Objects",
    "FA-Spiders",
    "FA-Emissive",
    "Fresh Moves",
    "JustExpressions",
    "eating_animations_x_farmers_delight",
    "Darkmode",
    "Modded",
    "Immersive",
    "Icons v.1.14",
    "enchant icons 1.21",
    "Enchantment-Outlines",
    "Visual Titles",
    "Enhanced Boss Bars",
    "slightly-improved-font",
    "updated_aquaculture",
    "Boundless R1 Resource Compatibility",
]


def selected_resourcepacks() -> list[str]:
    meta = json.loads((ROOT / "minecraftinstance.json").read_text(encoding="utf-8-sig"))
    selected = [
        item["fileNameOnDisk"]
        for item in meta["installedAddons"]
        if item.get("categorySection", {}).get("path") == "resourcepacks"
    ]
    if len(selected) != 40 or len(set(selected)) != 40:
        raise RuntimeError(f"Expected 40 unique CurseForge resource packs, found {len(selected)}")
    for name in selected:
        if not (RESOURCEPACKS / name).is_file():
            raise FileNotFoundError(RESOURCEPACKS / name)
    return selected


def build_font_merge() -> bytes:
    icons = RESOURCEPACKS / "Icons v.1.14.zip"
    enchant = RESOURCEPACKS / "enchant icons 1.21 v1.3.zip"
    providers: list[dict] = []
    with zipfile.ZipFile(icons) as zf:
        root = json.loads(zf.read("assets/minecraft/font/default.json"))
        for provider in root.get("providers", []):
            if provider.get("type") == "reference":
                resource = provider["id"].split(":", 1)[-1]
                child = json.loads(zf.read(f"assets/minecraft/font/{resource}.json"))
                providers.extend(child.get("providers", []))
            else:
                providers.append(provider)
    with zipfile.ZipFile(enchant) as zf:
        root = json.loads(zf.read("assets/minecraft/font/default.json"))
        providers.extend(root.get("providers", []))

    # Fresh Animations' two selected extensions each declare U+F7FF through
    # the same font path, but that referenced PNG is absent from both archives.
    # Neither marker is a world animation; omitting the dead glyph prevents a
    # duplicate-codepoint and missing-bitmap warning while preserving models.
    if len(providers) != len({json.dumps(p, sort_keys=True, ensure_ascii=True) for p in providers}):
        raise RuntimeError("Duplicate provider declarations in font merge inputs")
    seen: dict[str, dict] = {}
    for provider in providers:
        for row in provider.get("chars", []):
            for char in row:
                if char == "\u0000":
                    continue
                if char in seen:
                    raise RuntimeError(f"Conflicting font codepoint U+{ord(char):04X}")
                seen[char] = provider
    return (json.dumps({"providers": providers}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def create_overlay(font: bytes) -> None:
    mcmeta = {
        "pack": {
            "pack_format": 34,
            "supported_formats": {"min_inclusive": 34, "max_inclusive": 34},
            "description": "Boundless v2 R1: merged font providers for selected UI and enchantment packs",
        }
    }
    path = RESOURCEPACKS / COMPAT_NAME
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pack.mcmeta", json.dumps(mcmeta, ensure_ascii=False, indent=2) + "\n")
        zf.writestr("assets/minecraft/font/default.json", font)


def update_options(ordered: list[str]) -> None:
    lines = OPTIONS.read_text(encoding="utf-8").splitlines()
    file_ids = [f"file/{name}" for name in ordered]
    out = []
    found = False
    for line in lines:
        if line.startswith("resourcePacks:"):
            current = json.loads(line.split(":", 1)[1])
            ids = [pack for pack in current if not pack.startswith("file/")] + file_ids
            out.append("resourcePacks:" + json.dumps(ids, ensure_ascii=False, separators=(",", ":")))
            found = True
        else:
            out.append(line)
    if not found:
        raise RuntimeError("resourcePacks property not found in options.txt")
    OPTIONS.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_priority(ordered: list[str]) -> None:
    rows = []
    for rank, name in enumerate(ordered, start=1):
        reason = "CurseForge pack kept enabled; explicit low-to-high priority"
        if name == "FreshAnimations_v1.11.2_1.20.zip":
            reason = "Prioritized over the zombie texture pack where their CEM models collide"
        elif name.startswith("FA-") or name == "FA-All_Extensions-v1.10.1.zip":
            reason = "Animation extension overlays the Fresh Animations base pack"
        elif "Modded" in name:
            reason = "Specialized mod GUI textures override broad dark UI themes"
        elif name == COMPAT_NAME:
            reason = "Highest priority: supplies the merged custom-font provider registry"
        rows.append({"priority_low_to_high": rank, "file": name, "enabled": "yes", "reason": reason})
    with (AUDIT / "resourcepacks-order.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["priority_low_to_high", "file", "enabled", "reason"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    selected = selected_resourcepacks()
    by_token: dict[str, str] = {}
    for token in PRIORITY:
        matches = [name for name in selected if token.casefold() in name.casefold()]
        if token == "Boundless R1 Resource Compatibility":
            by_token[token] = COMPAT_NAME
        else:
            if len(matches) != 1:
                raise RuntimeError(f"Expected one pack matching {token!r}, got {matches}")
            by_token[token] = matches[0]
    ordered = list(by_token.values())
    if len(ordered) != 41 or len(set(ordered)) != 41:
        raise RuntimeError(f"Priority list should contain 40 selected packs plus overlay, got {len(ordered)}")
    font = build_font_merge()
    overlay = RESOURCEPACKS / COMPAT_NAME
    if not overlay.exists():
        create_overlay(font)
    else:
        with zipfile.ZipFile(overlay) as archive:
            if archive.read("assets/minecraft/font/default.json") != font:
                raise RuntimeError(f"Existing overlay differs from the generated font: {overlay}")
    update_options(ordered)
    write_priority(ordered)
    print(json.dumps({"selected_packs": len(selected), "compatibility_overlay": COMPAT_NAME,
                      "active_file_pack_ids": 41, "merged_font_providers": len(json.loads(font)["providers"]),
                      "order": str(AUDIT / "resourcepacks-order.csv")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
