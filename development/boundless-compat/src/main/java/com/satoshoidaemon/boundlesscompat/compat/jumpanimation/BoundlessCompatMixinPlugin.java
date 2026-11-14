package com.satoshoidaemon.boundlesscompat.compat.jumpanimation;

import com.mojang.logging.LogUtils;
import com.satoshoidaemon.boundlesscompat.runtime.JumpAnimationPatchGate;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;
import org.slf4j.Logger;

import java.util.List;
import java.util.Set;

public final class BoundlessCompatMixinPlugin implements IMixinConfigPlugin {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String JUMP_ANIMATION_MIXIN =
            "com.satoshoidaemon.boundlesscompat.compat.jumpanimation.JumpAnimationNullGameModeMixin";

    @Override
    public void onLoad(String mixinPackage) {
    }

    @Override
    public String getRefMapperConfig() {
        return null;
    }

    @Override
    public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
        if (!JUMP_ANIMATION_MIXIN.equals(mixinClassName)) {
            return true;
        }

        boolean apply = JumpAnimationPatchGate.shouldApplyMixin();
        JumpAnimationPatchGate.Snapshot snapshot = JumpAnimationPatchGate.snapshot();
        if (apply) {
            LOGGER.info("JumpAnimation {} detected; enabling Boundless null-gameMode guard.",
                    snapshot.detectedVersion());
        } else {
            LOGGER.info("JumpAnimation guard not selected: version={}, gate={}",
                    snapshot.detectedVersion(), snapshot.status());
        }
        return apply;
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
        if (JUMP_ANIMATION_MIXIN.equals(mixinClassName)) {
            JumpAnimationPatchGate.markMixinApplied(targetClassName);
        }
    }
}
