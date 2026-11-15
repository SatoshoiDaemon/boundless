package com.satoshoidaemon.boundlessfix;

import com.mojang.logging.LogUtils;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;
import org.slf4j.Logger;

import java.io.IOException;

@Mod(BoundlessFix.MOD_ID)
public final class BoundlessFix {
    public static final String MOD_ID = "boundlessfix";
    private static final String DAYZOMBIE_MOD_ID = "dayzombierebooted";
    private static final Logger LOGGER = LogUtils.getLogger();

    public BoundlessFix() {
        if (!ModList.get().isLoaded(DAYZOMBIE_MOD_ID)) {
            return;
        }

        try {
            if (DayzombieConfigBootstrap.createIfMissing(
                    FMLPaths.CONFIGDIR.get(),
                    () -> BoundlessFix.class.getResourceAsStream("/config/dayzombiesconfig"))) {
                LOGGER.info("Created the extensionless Dayzombie Rebooted config at config/dayzombiesconfig.");
            }
        } catch (IOException exception) {
            LOGGER.error("Could not create config/dayzombiesconfig for Dayzombie Rebooted.", exception);
        }
    }
}
