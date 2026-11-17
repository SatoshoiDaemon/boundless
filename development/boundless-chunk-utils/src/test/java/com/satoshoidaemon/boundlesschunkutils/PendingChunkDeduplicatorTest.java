package com.satoshoidaemon.boundlesschunkutils;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PendingChunkDeduplicatorTest {
    @Test
    void deduplicatesWithinOneDimensionAndTickButAllowsAnotherDimension() {
        PendingChunkDeduplicator pending = new PendingChunkDeduplicator();

        assertTrue(pending.markQueued("overworld", 0x100000001L));
        assertFalse(pending.markQueued("overworld", 0x100000001L));
        assertTrue(pending.markQueued("nether", 0x100000001L));
    }

    @Test
    void clearsPositionsAfterTheStagingListIsDrained() {
        PendingChunkDeduplicator pending = new PendingChunkDeduplicator();
        assertTrue(pending.markQueued("overworld", 42L));

        pending.resetForNextTick();

        assertTrue(pending.markQueued("overworld", 42L));
    }
}
