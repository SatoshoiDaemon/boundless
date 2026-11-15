package com.satoshoidaemon.boundlesstweaks.diagnostics;

import com.mojang.brigadier.CommandDispatcher;
import com.satoshoidaemon.boundlesstweaks.BoundlessTweaks;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.Locale;

@Mod.EventBusSubscriber(modid = BoundlessTweaks.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class PerformanceCommand {
    private PerformanceCommand() {
    }

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("boundless")
                .then(Commands.literal("perf")
                        .executes(context -> report(context.getSource()))));
    }

    private static int report(CommandSourceStack source) {
        TickWindow.Snapshot snapshot = TickWindow.snapshot();
        if (snapshot.sampleCount() == 0) {
            source.sendSuccess(() -> Component.literal("[Boundless Tweaks] No server ticks captured yet."), false);
            return 0;
        }

        double meanMs = snapshot.meanMs();
        double equivalentTps = meanMs > 0.0 ? Math.min(20.0, 1000.0 / meanMs) : 20.0;
        String line = String.format(
                Locale.ROOT,
                "[Boundless Tweaks] Last %d server ticks over %.1f s: mean %.2f ms, p50 %.2f ms, p95 %.2f ms, p99 %.2f ms, max %.2f ms; mean-time TPS equivalent %.2f.",
                snapshot.sampleCount(),
                snapshot.spanSeconds(),
                meanMs,
                snapshot.percentileMs(0.50),
                snapshot.percentileMs(0.95),
                snapshot.percentileMs(0.99),
                snapshot.maxMs(),
                equivalentTps
        );
        source.sendSuccess(() -> Component.literal(line), false);
        return snapshot.sampleCount();
    }
}
