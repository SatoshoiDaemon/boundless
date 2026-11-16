# HeadlessMC remote tests

The `Boundless Headless Remote Tests` workflow runs a clean Linux client through HeadlessMC and MC-Runtime-Test. It does not read a local game profile, personal save, or Windows installation. It can be started from the GitHub Actions page on a phone, called from another workflow, or triggered by pushes that change the pack, custom mods, or test harness.

## Start from GitHub

1. Open the repository's **Actions** tab and select **Boundless Headless Remote Tests**.
2. Tap **Run workflow**.
3. Enter a branch, tag, or commit SHA in `target_ref`.
4. Choose `test_level`; for the world tier, choose `bcl_experiment`.
5. Open the finished run summary. Download the `boundless-headless-*` artifact for raw logs, test reports, JFR, GC logs, and CSV metrics.

## Test levels

| Level | What runs |
| --- | --- |
| `bootstrap` | HeadlessMC installs the pinned Minecraft/Forge runtime, starts MC-Runtime-Test, creates a fresh single-player world, and exits. No Boundless mod is staged. |
| `forge` | Builds the CI harness and requires Forge 47.4.28 plus registered Forge GameTests. |
| `boundless-mods` | Builds and stages Boundless Compat, Fix, and Tweaks; verifies that all three load in the test world. |
| `full-modpack` | Checks out all versioned mod JARs and LFS objects, stages the pack configuration and scripts, opens a world, and verifies the full runtime mod list. |
| `world` | Runs the full pack and a fixed-seed movement/world workload for 1,200 ticks. The default `ab` setting runs a clean `enablePrediction=true` pass and a clean `false` pass with the same seed. |

`bcl_experiment` accepts `none`, `on`, `off`, or `ab`. Each condition gets a fresh save and separate logs. `none` keeps the pack's checked-in config value. The A/B order is on then off; this first pair is a remote exploratory benchmark, not a repeated statistical study.

## Results and limits

The run summary records the selected revision, staged mod hashes, Forge version, loaded mod counts, test outcomes, crash reports, tick-work and tick-interval CSVs, memory samples, runner memory/CPU sampling, JFR, and GC logs where the level provides them. HeadlessMC, its Forge build, and the MC-Runtime-Test jar are downloaded from pinned releases and checked against the versioned runtime lock; the Minecraft runtime cache is stored in GitHub Actions. `tick_work_ms` is measured between Forge server tick START and END events; `tick_interval_ms` includes the server's normal 20 TPS pacing.

Every performance number is labeled as a GitHub `ubuntu-latest` Linux runner benchmark. Compare the two Better Chunk Loading conditions only when both have the same seed and workload. These values are not interchangeable with measurements from the Windows PC.

The workflow pins its GitHub Actions, HeadlessMC, MC-Runtime-Test, Minecraft, Forge, Java major version, and the repository's exact mod/config content. A failed check leaves the captured artifacts attached to the run before the final job step reports failure.
