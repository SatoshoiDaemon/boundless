package com.satoshoidaemon.boundlesschunkutils.mixin.betterchunkloading;

import com.mojang.logging.LogUtils;
import com.satoshoidaemon.boundlesschunkutils.PendingChunkDeduplicator;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.slf4j.Logger;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/** Prevents same-tick duplicate post-processing entries before BCL drains its staging list. */
@Mixin(targets = "com.betterchunkloading.event.EventHandler", remap = false)
@Pseudo
public abstract class EventHandlerQueueDedupMixin {
    @Unique private static final Logger boundless$logger = LogUtils.getLogger();
    @Unique private static final AtomicBoolean boundless$disabled = new AtomicBoolean();

    @Redirect(
            method = "addChunkToQueue",
            at = @At(value = "INVOKE", target = "Ljava/util/List;add(Ljava/lang/Object;)Z", remap = false),
            remap = false)
    private static boolean boundless$addChunkInfoOnce(List<?> stagingList, @Coerce Object chunkInfo) {
        if (boundless$disabled.get()) {
            return boundless$append(stagingList, chunkInfo);
        }

        if (!(chunkInfo instanceof BclChunkInfoAccessor access)) {
            boundless$disable(new IllegalStateException("Better Chunk Loading ChunkInfo accessor was not applied"));
            return boundless$append(stagingList, chunkInfo);
        }

        try {
            Level level = access.boundless$getLevel();
            ChunkPos position = access.boundless$getChunkPos();
            MinecraftServer server = level == null ? null : level.getServer();
            if (level == null || position == null || server == null || !server.isSameThread()) {
                return boundless$append(stagingList, chunkInfo);
            }

            if (!PendingChunkDeduplicator.shared().markQueued(level.dimension(), position.toLong())) {
                return false;
            }
        } catch (RuntimeException | LinkageError error) {
            boundless$disable(error);
            return boundless$append(stagingList, chunkInfo);
        }

        return boundless$append(stagingList, chunkInfo);
    }

    @Unique
    @SuppressWarnings("unchecked")
    private static boolean boundless$append(List<?> stagingList, Object chunkInfo) {
        return ((List<Object>) stagingList).add(chunkInfo);
    }

    @Unique
    private static void boundless$disable(Throwable error) {
        if (boundless$disabled.compareAndSet(false, true)) {
            boundless$logger.error("Disabling chunk queue deduplication and passing chunks through unchanged.", error);
        }
    }
}
