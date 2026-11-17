package com.satoshoidaemon.boundlessfix;

import com.mojang.logging.LogUtils;
import net.minecraftforge.fml.loading.FMLLoader;
import net.minecraftforge.fml.loading.LoadingModList;
import net.minecraftforge.fml.loading.moddiscovery.ModInfo;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;
import org.slf4j.Logger;

import java.util.List;
import java.util.Optional;
import java.util.Set;

public final class BoundlessFixMixinPlugin implements IMixinConfigPlugin {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String ILLAGE_MIXIN =
            "com.satoshoidaemon.boundlessfix.mixin.illage.IllageProjectileCategoryMixin";
    private static final String CLIMBER_MIXIN =
            "com.satoshoidaemon.boundlessfix.mixin.spider.ClimberComponentCollisionScanMixin";

    @Override
    public void onLoad(String mixinPackage) {
    }

    @Override
    public String getRefMapperConfig() {
        return null;
    }

    @Override
    public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
        if (!ILLAGE_MIXIN.equals(mixinClassName)) {
            return !CLIMBER_MIXIN.equals(mixinClassName) || shouldApplyClimberMixin(FMLLoader.getLoadingModList());
        }

        return shouldApplyIllageMixin(FMLLoader.getLoadingModList());
    }

    static boolean shouldApplyClimberMixin(LoadingModList loadingMods) {
        if (loadingMods == null) {
            LOGGER.warn("Spider collision optimization is disabled because Forge's loading mod list is unavailable.");
            return false;
        }

        return loadingMods.getMods().stream()
                .filter(mod -> ClimberCollisionOptimization.MOD_ID.equals(mod.getModId()))
                .findFirst()
                .map(mod -> {
                    String version = mod.getVersion().toString();
                    boolean supported = ClimberCollisionOptimization.supports(mod.getModId(), version);
                    if (supported) {
                        LOGGER.info("Applying the allocation-free spider collision scan for AWCAPI {}.", version);
                    } else {
                        LOGGER.warn("Spider collision optimization is disabled: supported AWCAPI version is {}.",
                                ClimberCollisionOptimization.SUPPORTED_VERSION);
                    }
                    return supported;
                })
                .orElse(false);
    }

    static boolean shouldApplyIllageMixin(LoadingModList loadingMods) {
        if (loadingMods == null) {
            LOGGER.warn("Illage projectile category patch is disabled because Forge's loading mod list is unavailable.");
            return false;
        }

        Optional<ModInfo> illage = loadingMods.getMods().stream()
                .filter(mod -> IllageProjectileCategoryFix.MOD_ID.equals(mod.getModId()))
                .findFirst();
        if (illage.isEmpty()) {
            return false;
        }

        String version = illage.get().getVersion().toString();
        boolean supported = IllageProjectileCategoryFix.supports(illage.get().getModId(), version);

        if (supported) {
            LOGGER.info("Correcting Illage and Spillage projectile categories for {}.",
                    version);
        } else {
            LOGGER.warn("Illage projectile category patch is disabled: supported version is {}.",
                    IllageProjectileCategoryFix.SUPPORTED_VERSION);
        }
        return supported;
    }

    @Override
    public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) {
    }

    @Override
    public List<String> getMixins() {
        return null;
    }

    @Override
    public void preApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {
    }

    @Override
    public void postApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {
    }
}
