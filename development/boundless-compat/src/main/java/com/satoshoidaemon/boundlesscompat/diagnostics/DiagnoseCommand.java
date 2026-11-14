package com.satoshoidaemon.boundlesscompat.diagnostics;

import com.mojang.brigadier.CommandDispatcher;
import com.satoshoidaemon.boundlesscompat.BoundlessCompat;
import com.satoshoidaemon.boundlesscompat.config.BoundlessCompatConfig;
import com.satoshoidaemon.boundlesscompat.runtime.JumpAnimationPatchGate;
import net.minecraft.SharedConstants;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.ModContainer;
import net.minecraftforge.fml.common.Mod;

import java.util.List;
import java.util.Optional;

@Mod.EventBusSubscriber(modid = BoundlessCompat.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class DiagnoseCommand {
    private static final List<String> RELEVANT_MODS = List.of(
            "jumpanimation",
            "bettercombat",
            "mowziesmobs",
            "born_in_chaos_v1"
    );

    private DiagnoseCommand() {
    }

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("boundless")
                .then(Commands.literal("diagnose")
                        .executes(context -> diagnose(context.getSource()))));
    }

    private static int diagnose(CommandSourceStack source) {
        source.sendSuccess(() -> Component.literal("Boundless Compat v" + modVersion(BoundlessCompat.MOD_ID)
                + " environment"), false);
        source.sendSuccess(() -> Component.literal("Minecraft " + SharedConstants.getCurrentVersion().getName()
                + " | Java " + System.getProperty("java.version")), false);
        source.sendSuccess(() -> Component.literal("Forge " + modVersion("forge")
                + " | Boundless Compat " + modVersion(BoundlessCompat.MOD_ID)), false);

        for (String modId : RELEVANT_MODS) {
            source.sendSuccess(() -> Component.literal("Mod " + modId + ": " + modVersion(modId)), false);
        }

        JumpAnimationPatchGate.Snapshot gate = JumpAnimationPatchGate.snapshot();
        String enabled = configEnabled();
        source.sendSuccess(() -> Component.literal("JumpAnimation null-gameMode guard: config=" + enabled
                + ", detected=" + gate.detectedVersion()
                + ", version gate=" + gate.status()
                + ", mixin applied=" + gate.mixinApplied()
                + ", guard triggered=" + gate.guardTriggered()
                + ", intercept count=" + gate.guardTriggerCount()), false);
        return 1;
    }

    private static String modVersion(String modId) {
        Optional<? extends ModContainer> container = ModList.get().getModContainerById(modId);
        return container.map(value -> value.getModInfo().getVersion().toString()).orElse("not installed");
    }

    private static String configEnabled() {
        try {
            return Boolean.toString(BoundlessCompatConfig.JUMPANIMATION_NULL_GAMEMODE_GUARD.get());
        } catch (IllegalStateException exception) {
            return "not loaded (client config)";
        }
    }
}
