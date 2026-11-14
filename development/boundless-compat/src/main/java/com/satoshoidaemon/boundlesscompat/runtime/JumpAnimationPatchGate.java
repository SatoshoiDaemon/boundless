package com.satoshoidaemon.boundlesscompat.runtime;

import com.mojang.logging.LogUtils;
import net.minecraftforge.fml.loading.FMLLoader;
import net.minecraftforge.fml.loading.LoadingModList;
import net.minecraftforge.forgespi.language.IModInfo;
import org.slf4j.Logger;

import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

public final class JumpAnimationPatchGate {
    public static final String MOD_ID = "jumpanimation";
    public static final String SUPPORTED_VERSION = "2.0.0";
    public static final String TARGET_CLASS = "com.saltywater.jumpanimation.JumpAnimationClient";

    private static final Logger LOGGER = LogUtils.getLogger();

    private static volatile Status status = Status.NOT_CHECKED;
    private static volatile String detectedVersion = "not checked";
    private static volatile boolean mixinApplied;
    private static final AtomicLong guardTriggerCount = new AtomicLong();

    private JumpAnimationPatchGate() {
    }

    public static boolean shouldApplyMixin() {
        try {
            LoadingModList loadingModList = FMLLoader.getLoadingModList();
            if (loadingModList == null) {
                detectedVersion = "loading mod list unavailable";
                status = Status.CHECK_FAILED;
                return false;
            }

            Optional<IModInfo> modInfo = loadingModList.getMods().stream()
                    .filter(info -> MOD_ID.equals(info.getModId()))
                    .map(info -> (IModInfo) info)
                    .findFirst();
            if (modInfo.isEmpty()) {
                detectedVersion = "not installed";
                status = Status.MOD_NOT_INSTALLED;
                return false;
            }

            detectedVersion = modInfo.get().getVersion().toString();
            if (SUPPORTED_VERSION.equals(detectedVersion)) {
                status = Status.SUPPORTED_VERSION;
                return true;
            }

            status = Status.UNSUPPORTED_VERSION;
            return false;
        } catch (RuntimeException | LinkageError error) {
            detectedVersion = "unavailable during Mixin selection";
            status = Status.CHECK_FAILED;
            return false;
        }
    }

    public static Snapshot snapshot() {
        return new Snapshot(status, detectedVersion, mixinApplied, guardTriggerCount.get());
    }

    public static void markMixinApplied(String targetClassName) {
        if (!TARGET_CLASS.equals(targetClassName)) {
            LOGGER.error("JumpAnimation guard Mixin reported an unexpected target: {}", targetClassName);
            return;
        }

        mixinApplied = true;
        LOGGER.info("Applied Boundless null-gameMode guard to {}.isPlayerInSurvival(LocalPlayer).",
                TARGET_CLASS);
    }

    public static void markGuardTriggered() {
        long triggerCount = guardTriggerCount.incrementAndGet();
        if (triggerCount == 1) {
            LOGGER.info("Intercepted {}.isPlayerInSurvival: Minecraft.gameMode was null; returned false.",
                    TARGET_CLASS);
        }
    }

    public enum Status {
        NOT_CHECKED,
        MOD_NOT_INSTALLED,
        SUPPORTED_VERSION,
        UNSUPPORTED_VERSION,
        CHECK_FAILED
    }

    public record Snapshot(Status status, String detectedVersion, boolean mixinApplied, long guardTriggerCount) {
        public boolean guardTriggered() {
            return guardTriggerCount > 0;
        }
    }
}
