package com.satoshoidaemon.boundlessfix;

public final class ClimberCollisionOptimization {
    public static final String MOD_ID = "awcapi";
    public static final String SUPPORTED_VERSION = "1.0.3";

    private ClimberCollisionOptimization() {
    }

    public static boolean supports(String modId, String version) {
        return MOD_ID.equals(modId) && SUPPORTED_VERSION.equals(version);
    }
}
