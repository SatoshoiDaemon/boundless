package com.satoshoidaemon.boundlesscompat.config;

import net.minecraftforge.common.ForgeConfigSpec;

public final class BoundlessCompatConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue JUMPANIMATION_NULL_GAMEMODE_GUARD;

    static {
        ForgeConfigSpec.Builder builder = new ForgeConfigSpec.Builder();
        builder.push("compat");
        JUMPANIMATION_NULL_GAMEMODE_GUARD = builder
                .comment("Skip JumpAnimation's survival check while the client has no game mode. Requires JumpAnimation 2.0.0.")
                .define("jumpAnimationNullGameModeGuard", true);
        builder.pop();
        SPEC = builder.build();
    }

    private BoundlessCompatConfig() {
    }
}
