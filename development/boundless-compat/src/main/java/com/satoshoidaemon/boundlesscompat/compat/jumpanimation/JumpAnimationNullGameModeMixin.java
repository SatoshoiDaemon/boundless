package com.satoshoidaemon.boundlesscompat.compat.jumpanimation;

import com.satoshoidaemon.boundlesscompat.config.BoundlessCompatConfig;
import com.satoshoidaemon.boundlesscompat.runtime.JumpAnimationGuard;
import com.satoshoidaemon.boundlesscompat.runtime.JumpAnimationPatchGate;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets = "com.saltywater.jumpanimation.JumpAnimationClient", remap = false)
@Pseudo
public abstract class JumpAnimationNullGameModeMixin {
    @Inject(
            method = "isPlayerInSurvival(Lnet/minecraft/client/player/LocalPlayer;)Z",
            at = @At("HEAD"),
            cancellable = true,
            remap = false
    )
    private void boundlessCompat$skipWhenGameModeIsMissing(
            LocalPlayer player,
            CallbackInfoReturnable<Boolean> callback
    ) {
        boolean enabled = BoundlessCompatConfig.JUMPANIMATION_NULL_GAMEMODE_GUARD.get();
        Object gameMode = Minecraft.getInstance().gameMode;
        if (JumpAnimationGuard.shouldReturnFalse(enabled, gameMode)) {
            JumpAnimationPatchGate.markGuardTriggered();
            callback.setReturnValue(false);
        }
    }
}
