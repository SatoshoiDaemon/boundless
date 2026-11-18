package com.satoshoidaemon.boundlesschunkutils;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.fml.common.Mod;

@Mod(BoundlessChunkUtils.MOD_ID)
public final class BoundlessChunkUtils {
    public static final String MOD_ID = "boundlesschunkutils";

    public BoundlessChunkUtils() {
        MinecraftForge.EVENT_BUS.addListener(EventPriority.LOWEST, this::afterServerTick);
        MinecraftForge.EVENT_BUS.addListener(EventPriority.LOWEST, this::onServerStopping);
    }

    private void afterServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END) {
            PendingChunkDeduplicator.shared().resetForNextTick();
        }
    }

    private void onServerStopping(ServerStoppingEvent event) {
        PendingChunkDeduplicator.shared().resetForNextTick();
    }
}
