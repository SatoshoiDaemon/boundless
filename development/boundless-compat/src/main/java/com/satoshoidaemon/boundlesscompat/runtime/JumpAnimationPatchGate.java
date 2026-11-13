package com.satoshoidaemon.boundlesscompat.runtime;

import net.minecraftforge.fml.loading.FMLLoader;
import net.minecraftforge.fml.loading.LoadingModList;
import net.minecraftforge.forgespi.language.IModInfo;

import java.util.Optional;

public final class JumpAnimationPatchGate {
    public static final String MOD_ID = "jumpanimation";
    public static final String SUPPORTED_VERSION = "2.0.0";

    private static volatile Status status = Status.NOT_CHECKED;
    private static volatile String detectedVersion = "not checked";
    private static volatile boolean guardTriggered;

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
        return new Snapshot(status, detectedVersion, guardTriggered);
    }

    public static void markGuardTriggered() {
        guardTriggered = true;
    }

    public enum Status {
        NOT_CHECKED,
        MOD_NOT_INSTALLED,
        SUPPORTED_VERSION,
        UNSUPPORTED_VERSION,
        CHECK_FAILED
    }

    public record Snapshot(Status status, String detectedVersion, boolean guardTriggered) {
    }
}
