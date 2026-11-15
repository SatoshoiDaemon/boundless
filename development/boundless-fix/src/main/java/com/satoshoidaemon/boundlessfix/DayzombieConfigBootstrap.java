package com.satoshoidaemon.boundlessfix;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.Supplier;

final class DayzombieConfigBootstrap {
    private static final String EXPECTED_FILE = "dayzombiesconfig";
    private static final String JSON_FILE = "dayzombiesconfig.json";

    private DayzombieConfigBootstrap() {
    }

    static boolean createIfMissing(Path configDirectory, Supplier<InputStream> bundledDefault) throws IOException {
        Path expected = configDirectory.resolve(EXPECTED_FILE);
        if (Files.exists(expected)) {
            if (!Files.isRegularFile(expected)) {
                throw new IOException("Expected Dayzombie config path is not a regular file: " + expected);
            }
            return false;
        }

        Files.createDirectories(configDirectory);
        Path jsonConfig = configDirectory.resolve(JSON_FILE);
        if (Files.exists(jsonConfig)) {
            if (!Files.isRegularFile(jsonConfig)) {
                throw new IOException("Dayzombie JSON config path is not a regular file: " + jsonConfig);
            }
            Files.copy(jsonConfig, expected);
            return true;
        }

        try (InputStream input = bundledDefault.get()) {
            if (input == null) {
                throw new IOException("Bundled Dayzombie default config is missing.");
            }
            Files.copy(input, expected);
            return true;
        }
    }
}
