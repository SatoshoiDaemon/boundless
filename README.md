# Boundless

Boundless is an RPG-focused modpack for Minecraft 1.20.1. It brings together broad exploration, tougher encounters, and character progression built around weapons, magic, equipment, and loot. The pack is designed to make a new world feel full of places to discover and challenges worth preparing for.

## The Boundless experience

- **Explore:** Expanded terrain, biomes, and structures from mods such as Terralith, Tectonic, Biomes O' Plenty, and YUNG's Better series give expeditions more variety.
- **Fight and progress:** Better Combat, Simply Swords, Iron's Spells 'n Spellbooks, Apotheosis, and Cataclysm support distinct combat builds, spellcasting, powerful gear, and memorable boss encounters.
- **Make it yours:** Resource packs, shader packs, client options, and configured mods let players shape the look and feel of their world.

## Game version

- Minecraft **1.20.1**
- Forge **47.4.28**
- Java **17**

## Play through CurseForge

CurseForge is the player-facing installation and launch path. Once the Boundless profile is published there, install it from its official project page and launch it in the app. The profile targets Minecraft 1.20.1 and Forge 47.4.28.

To run a development snapshot through CurseForge, create a matching custom profile in the app, open its folder, then copy these directories from the Boundless working tree into it:

```text
mods/
config/
defaultconfigs/
kubejs/
resourcepacks/
shaderpacks/
```

If the working tree has files under `datapacks/`, copy that directory as well. Keep directory names and paths intact, then launch the profile from CurseForge. See the [CurseForge custom profile guide](https://support.curseforge.com/support/solutions/articles/9000196904) for creating a profile.

## Work on the pack

Git is used for development, collaboration, and version history. The checkout contains the complete instance state so contributors can review and test the same pack that players install through CurseForge.

Install Git LFS, then clone the repository and fetch its large files:

```powershell
git lfs install
git clone https://github.com/SatoshoiDaemon/boundless.git
cd boundless
git lfs pull
```

Make gameplay changes in the corresponding instance directories. `scripts/`, `patches/`, and `development/` contain project tooling and compatibility work; `docs/`, `manifests/`, and `auditoria/` provide maintainer guides and technical references for understanding and troubleshooting the pack.

For remote testing without the local PC, run **Boundless Headless Remote Tests** from the GitHub Actions tab. It can build custom mods, load the full pack, create a seeded world, and capture Linux runner logs and metrics. See [the remote test guide](docs/headless-mc-ci.md) for the test levels and Better Chunk Loading experiment.
