package com.satoshoidaemon.boundlessheadlesstest;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.worldselection.CreateWorldScreen;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.gametest.framework.GameTestRegistry;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.ModContainer;
import net.minecraftforge.fml.common.Mod;
import org.slf4j.Logger;
import com.mojang.logging.LogUtils;


@Mod(BoundlessHeadlessTest.MOD_ID)
public final class BoundlessHeadlessTest {
    public static final String MOD_ID = "boundless_headless_test";
    private static final Logger LOGGER = LogUtils.getLogger();

    public BoundlessHeadlessTest() {
        GameTestRegistry.register(HeadlessWorldGameTests.class);
        GameTestRegistry.register(ForgeSmokeTests.class);
        MinecraftForge.EVENT_BUS.register(this);
        LOGGER.info("Boundless headless harness loaded; mod_count={}", ModList.get().getMods().size());
    }

    @SubscribeEvent
    public void onCreateWorldScreen(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof CreateWorldScreen)) {
            return;
        }

        CreateWorldScreen screen = (CreateWorldScreen) event.getScreen();
        String seed = WorldRun.seedText();
        screen.getUiState().setSeed(seed);
        boolean applied = seed.equals(screen.getUiState().getSeed());
        WorldRun.markSeedApplied(applied);
        if (applied) {
            LOGGER.info("BOUNDLESS_HEADLESS_SEED applied seed={} to the fresh world screen", seed);
        } else {
            LOGGER.error("BOUNDLESS_HEADLESS_SEED could not set seed={} on world creation state", seed);
        }
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !WorldRun.isActive()) {
            return;
        }

        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || minecraft.level == null || minecraft.getSingleplayerServer() == null) {
            return;
        }

        if (WorldRun.shouldMove()) {
            minecraft.options.keyUp.setDown(true);
            minecraft.options.keySprint.setDown(true);
            minecraft.options.keyJump.setDown(true);
        } else {
            minecraft.options.keyUp.setDown(false);
            minecraft.options.keySprint.setDown(false);
            minecraft.options.keyJump.setDown(false);
        }
        WorldRun.recordPosition(player.getX(), player.getZ());
    }

    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.START && WorldRun.isActive()) {
            WorldRun.startServerTick();
        } else if (event.phase == TickEvent.Phase.END && WorldRun.isActive()) {
            WorldRun.recordServerTick();
        }
    }

    static boolean hasBetterChunkLoading() {
        return ModList.get().isLoaded("betterchunkloading");
    }

    static int loadedModCount() {
        return ModList.get().getMods().size();
    }

    static String forgeVersion() {
        return ModList.get().getModContainerById("forge")
                .map(ModContainer::getModInfo)
                .map(info -> info.getVersion().toString())
                .orElse("unknown");
    }

    static void beginWorkload(ServerLevel level) {
        MinecraftServer server = level.getServer();
        WorldRun.begin(level, server.getTickCount(), hasBetterChunkLoading(), loadedModCount());
    }
}
