package com.satoshoidaemon.boundlesscompat.runtime;

/** Small, side-effect-free predicate for the null-game-mode regression guard. */
public final class JumpAnimationGuard {
    private JumpAnimationGuard() {
    }

    public static boolean shouldReturnFalse(boolean enabled, Object gameMode) {
        return enabled && gameMode == null;
    }
}
