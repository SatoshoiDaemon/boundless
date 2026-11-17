package com.satoshoidaemon.boundlesschunkutils;

public final class BetterChunkLoadingTarget {
    public static final String MOD_ID = "betterchunkloading";
    public static final String SUPPORTED_VERSION = "1.20.1-5.4";

    private BetterChunkLoadingTarget() {
    }

    public static boolean supports(String modId, String version) {
        return MOD_ID.equals(modId) && SUPPORTED_VERSION.equals(version);
    }
}
