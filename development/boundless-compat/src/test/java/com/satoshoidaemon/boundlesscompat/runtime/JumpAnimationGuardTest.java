package com.satoshoidaemon.boundlesscompat.runtime;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JumpAnimationGuardTest {
    @Test
    void returnsFalseWhenEnabledAndGameModeIsNull() {
        assertTrue(JumpAnimationGuard.shouldReturnFalse(true, null));
    }

    @Test
    void leavesNormalGameModeAlone() {
        assertFalse(JumpAnimationGuard.shouldReturnFalse(true, new Object()));
    }

    @Test
    void disabledGuardLeavesOriginalMethodAloneEvenWhenGameModeIsNull() {
        assertFalse(JumpAnimationGuard.shouldReturnFalse(false, null));
    }

    @Test
    void disabledGuardLeavesNormalGameModeAlone() {
        assertFalse(JumpAnimationGuard.shouldReturnFalse(false, new Object()));
    }
}
