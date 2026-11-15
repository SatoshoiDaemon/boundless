package com.satoshoidaemon.boundlesstweaks.diagnostics;

import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import com.satoshoidaemon.boundlesstweaks.BoundlessTweaks;

@Mod.EventBusSubscriber(modid = BoundlessTweaks.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class TickMetricsSubscriber {
    private static long tickStartNs;

    private TickMetricsSubscriber() {
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onServerTickStart(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.START) {
            tickStartNs = System.nanoTime();
        }
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onServerTickEnd(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && tickStartNs != 0L) {
            long endNs = System.nanoTime();
            TickWindow.record(tickStartNs, endNs - tickStartNs);
            tickStartNs = 0L;
        }
    }

    @SubscribeEvent
    public static void onServerStarted(ServerStartedEvent event) {
        tickStartNs = 0L;
        TickWindow.reset();
    }
}
