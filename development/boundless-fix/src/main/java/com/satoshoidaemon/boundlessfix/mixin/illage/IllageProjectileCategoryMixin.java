package com.satoshoidaemon.boundlessfix.mixin.illage;

import com.satoshoidaemon.boundlessfix.IllageProjectileCategoryFix;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyArg;

@Mixin(targets = "com.yellowbrossproductions.illageandspillage.init.ModEntityTypes", remap = false)
@Pseudo
public abstract class IllageProjectileCategoryMixin {
    @ModifyArg(
            method = "lambda$static$30()Lnet/minecraft/world/entity/EntityType;",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/entity/EntityType$Builder;m_20704_(Lnet/minecraft/world/entity/EntityType$EntityFactory;Lnet/minecraft/world/entity/MobCategory;)Lnet/minecraft/world/entity/EntityType$Builder;",
                    remap = false
            ),
            index = 1,
            remap = false
    )
    private static MobCategory boundlessFix$boneCategory(MobCategory category) {
        return IllageProjectileCategoryFix.category("bone", category);
    }

    @ModifyArg(
            method = "lambda$static$40()Lnet/minecraft/world/entity/EntityType;",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/entity/EntityType$Builder;m_20704_(Lnet/minecraft/world/entity/EntityType$EntityFactory;Lnet/minecraft/world/entity/MobCategory;)Lnet/minecraft/world/entity/EntityType$Builder;",
                    remap = false
            ),
            index = 1,
            remap = false
    )
    private static MobCategory boundlessFix$axeCategory(MobCategory category) {
        return IllageProjectileCategoryFix.category("axe", category);
    }
}
