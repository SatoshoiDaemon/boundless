package com.satoshoidaemon.boundlesschunkutils;

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

public final class BoundlessChunkUtilsMixinPlugin implements IMixinConfigPlugin {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String QUEUE_MIXIN =
            "com.satoshoidaemon.boundlesschunkutils.mixin.betterchunkloading.EventHandlerQueueDedupMixin";
    private static final String ACCESSOR_MIXIN =
            "com.satoshoidaemon.boundlesschunkutils.mixin.betterchunkloading.BclChunkInfoAccessor";

    @Override
    public void onLoad(String mixinPackage) {
    }

    @Override
    public String getRefMapperConfig() {
        return null;
    }

    @Override
    public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
        if (!QUEUE_MIXIN.equals(mixinClassName) && !ACCESSOR_MIXIN.equals(mixinClassName)) {
            return true;
        }
        return supportsBetterChunkLoading(FMLLoader.getLoadingModList());
    }

    static boolean supportsBetterChunkLoading(LoadingModList loadingMods) {
        if (loadingMods == null) {
            return false;
        }

        Optional<ModInfo> mod = loadingMods.getMods().stream()
                .filter(candidate -> BetterChunkLoadingTarget.MOD_ID.equals(candidate.getModId()))
                .findFirst();
        if (mod.isEmpty()) {
            return false;
        }

        String version = mod.get().getVersion().toString();
        boolean supported = BetterChunkLoadingTarget.supports(mod.get().getModId(), version);
        if (supported) {
            LOGGER.info("Applying pending chunk post-processing deduplication for Better Chunk Loading {}.", version);
        } else {
            LOGGER.warn("Chunk queue optimization disabled for unsupported Better Chunk Loading version {}.", version);
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
