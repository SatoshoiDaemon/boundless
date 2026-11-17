package com.satoshoidaemon.boundlesschunkutils.mixin.betterchunkloading;

import net.minecraft.world.level.ChunkPos;
import net.minecraftforge.event.TickEvent;
import com.satoshoidaemon.boundlesschunkutils.PendingChunkDeduplicator;
import org.objectweb.asm.Opcodes;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.List;

/** Prevents same-tick duplicate post-processing entries before BCL drains its staging list. */
@Mixin(targets = "com.betterchunkloading.event.EventHandler", remap = false)
@Pseudo
public abstract class EventHandlerQueueDedupMixin {
    @Unique private static PendingChunkDeduplicator boundless$pendingChunks;

    @Redirect(
            method = "addChunkToQueue",
            at = @At(value = "INVOKE", target = "Ljava/util/List;add(Ljava/lang/Object;)Z", remap = false),
            remap = false)
    private static boolean boundless$addChunkInfoOnce(List<?> stagingList, @Coerce Object chunkInfo) {
        BclChunkInfoAccessor access = (BclChunkInfoAccessor) chunkInfo;
        ChunkPos position = access.boundless$getChunkPos();
        if (!boundless$pending().markQueued(access.boundless$getLevel().dimension(), position.toLong())) {
            return false;
        }
        @SuppressWarnings("unchecked")
        List<Object> writableStagingList = (List<Object>) stagingList;
        return writableStagingList.add(chunkInfo);
    }

    @Inject(
            method = "onServerTick",
            at = @At(value = "FIELD", target = "Lcom/betterchunkloading/event/EventHandler;toadd:Ljava/util/List;",
                    opcode = Opcodes.PUTSTATIC, shift = At.Shift.AFTER, remap = false),
            remap = false)
    private static void boundless$clearPendingKeysAfterDrain(TickEvent.ServerTickEvent event, CallbackInfo ci) {
        if (boundless$pendingChunks != null) {
            boundless$pendingChunks.resetForNextTick();
        }
    }

    @Unique
    private static PendingChunkDeduplicator boundless$pending() {
        if (boundless$pendingChunks == null) {
            boundless$pendingChunks = new PendingChunkDeduplicator();
        }
        return boundless$pendingChunks;
    }
}
