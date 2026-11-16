package com.satoshoidaemon.boundlessheadlesstest;

import com.google.gson.GsonBuilder;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.loading.FMLPaths;
import org.slf4j.Logger;
import com.mojang.logging.LogUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ForgeSmokeTests {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final List<String> BOUNDLESS_MODS = List.of(
            "boundlesscompat", "boundlessfix", "boundlesstweaks");

    private ForgeSmokeTests() {}

    @GameTest(template = "boundless_headless_test:empty", timeoutTicks = 1_000)
    public static void forgeRuntimeAndBoundlessMods(GameTestHelper helper) {
        List<String> loadedMods = new ArrayList<>();
        for (String modId : BOUNDLESS_MODS) {
            if (ModList.get().isLoaded(modId)) {
                loadedMods.add(modId);
            }
        }

        String forgeVersion = BoundlessHeadlessTest.forgeVersion();
        boolean requireBoundless = Boolean.getBoolean("boundless.headless.requireBoundlessMods");
        boolean requireBcl = Boolean.getBoolean("boundless.headless.requireBcl");
        boolean bclLoaded = ModList.get().isLoaded("betterchunkloading");
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("created_at_utc", Instant.now().toString());
        report.put("test_level", System.getProperty("boundless.headless.testLevel", "unknown"));
        report.put("minecraft_version", "1.20.1");
        report.put("forge_version", forgeVersion);
        report.put("loaded_mod_count", ModList.get().getMods().size());
        report.put("boundless_mods_loaded", loadedMods);
        report.put("better_chunk_loading_loaded", bclLoaded);
        report.put("gametest", "forgeRuntimeAndBoundlessMods");

        try {
            Path logs = FMLPaths.GAMEDIR.get().resolve("logs");
            Files.createDirectories(logs);
            Files.writeString(logs.resolve("headless-smoke-report.json"),
                    new GsonBuilder().setPrettyPrinting().create().toJson(report) + System.lineSeparator());
        } catch (IOException exception) {
            helper.fail("Could not write Forge smoke report: " + exception.getMessage());
            return;
        }

        String expectedForge = System.getProperty("boundless.headless.expectedForge", "47.4.28");
        if (!expectedForge.equals(forgeVersion)) {
            helper.fail("Expected Forge " + expectedForge + " but loaded " + forgeVersion);
            return;
        }
        if (requireBoundless && loadedMods.size() != BOUNDLESS_MODS.size()) {
            helper.fail("Not all Boundless development mods loaded: " + loadedMods);
            return;
        }
        if (System.getProperty("boundless.headless.testLevel", "").equals("full-modpack")
                && ModList.get().getMods().size() < 400) {
            helper.fail("Full modpack loaded fewer than 400 mods: " + ModList.get().getMods().size());
            return;
        }
        if (requireBcl && !bclLoaded) {
            helper.fail("Better Chunk Loading did not load in the selected pack tier");
            return;
        }

        LOGGER.info("BOUNDLESS_HEADLESS_SMOKE {}", new GsonBuilder().create().toJson(report));
        helper.succeed();
    }
}
