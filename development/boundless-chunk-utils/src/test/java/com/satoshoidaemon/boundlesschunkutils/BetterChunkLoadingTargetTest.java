package com.satoshoidaemon.boundlesschunkutils;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BetterChunkLoadingTargetTest {
    @Test
    void targetsOnlyThePackagedBetterChunkLoadingBuild() {
        assertTrue(BetterChunkLoadingTarget.supports("betterchunkloading", "1.20.1-5.4"));
        assertFalse(BetterChunkLoadingTarget.supports("betterchunkloading", "1.20.1-5.3"));
        assertFalse(BetterChunkLoadingTarget.supports("other", "1.20.1-5.4"));
    }
}
