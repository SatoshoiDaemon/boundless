package com.satoshoidaemon.boundlesschunkutils.mixin.betterchunkloading;

import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(targets = "com.betterchunkloading.event.EventHandler$ChunkInfo", remap = false)
@Pseudo
public interface BclChunkInfoAccessor {
    @Accessor(value = "pos", remap = false)
    ChunkPos boundless$getChunkPos();

    @Accessor(value = "level", remap = false)
    Level boundless$getLevel();
}
