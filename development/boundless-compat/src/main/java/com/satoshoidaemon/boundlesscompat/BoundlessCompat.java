package com.satoshoidaemon.boundlesscompat;

import com.satoshoidaemon.boundlesscompat.config.BoundlessCompatConfig;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;

@Mod(BoundlessCompat.MOD_ID)
public final class BoundlessCompat {
    public static final String MOD_ID = "boundlesscompat";

    public BoundlessCompat() {
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, BoundlessCompatConfig.SPEC);
    }
}
