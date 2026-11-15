package com.satoshoidaemon.boundlessfix;

import net.minecraft.world.entity.MobCategory;

public final class IllageProjectileCategoryFix {
    public static final String MOD_ID = "illageandspillage";
    public static final String SUPPORTED_VERSION = "1.2.8";

    private IllageProjectileCategoryFix() {
    }

    public static boolean supports(String modId, String version) {
        return MOD_ID.equals(modId) && SUPPORTED_VERSION.equals(version);
    }

    public static MobCategory category(String entityPath, MobCategory registeredCategory) {
        if (registeredCategory == MobCategory.MONSTER
                && ("bone".equals(entityPath) || "axe".equals(entityPath))) {
            return MobCategory.MISC;
        }
        return registeredCategory;
    }
}
