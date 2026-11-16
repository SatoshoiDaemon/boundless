package com.satoshoidaemon.boundlessheadlesstest;

import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import org.slf4j.Logger;
import com.mojang.logging.LogUtils;

public final class HeadlessWorldGameTests {
    private static final Logger LOGGER = LogUtils.getLogger();

    private HeadlessWorldGameTests() {}

    @GameTest(template = "boundless_headless_test:empty", timeoutTicks = 20_000)
    public static void generateSeededWorldAndMovePlayer(GameTestHelper helper) {
        if (!Boolean.getBoolean("boundless.headless.worldWorkload")) {
            helper.succeed();
            return;
        }

        if (!WorldRun.seedWasApplied()) {
            helper.fail("Headless test could not set the fixed world seed");
            return;
        }

        BoundlessHeadlessTest.beginWorkload(helper.getLevel());
        int durationTicks = WorldRun.requestedTicks();
        LOGGER.info("BOUNDLESS_HEADLESS_WORLD_BEGIN seed={} prediction={} duration_ticks={}",
                WorldRun.seedText(), WorldRun.predictionConfigured(), durationTicks);

        helper.runAtTickTime(durationTicks, () -> {
            try {
                WorldRun.finish(helper.getLevel().getServer().getTickCount());
                LOGGER.info("BOUNDLESS_HEADLESS_WORLD_RESULT {}", WorldRun.resultJson());
                helper.succeed();
            } catch (Exception exception) {
                LOGGER.error("Failed to write headless world metrics", exception);
                helper.fail("Failed to write headless world metrics: " + exception.getMessage());
            }
        });
    }
}
