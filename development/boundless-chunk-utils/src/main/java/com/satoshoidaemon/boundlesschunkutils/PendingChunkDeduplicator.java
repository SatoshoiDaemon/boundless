package com.satoshoidaemon.boundlesschunkutils;

import it.unimi.dsi.fastutil.longs.LongOpenHashSet;
import java.util.HashMap;
import java.util.Map;

/** Tracks positions queued for the current server tick without boxing chunk coordinates. */
public final class PendingChunkDeduplicator {
    private final Map<Object, LongOpenHashSet> positionsByDimension = new HashMap<>();

    public boolean markQueued(Object dimension, long chunkPos) {
        return positionsByDimension.computeIfAbsent(dimension, ignored -> new LongOpenHashSet()).add(chunkPos);
    }

    public void resetForNextTick() {
        positionsByDimension.values().forEach(LongOpenHashSet::clear);
    }
}
