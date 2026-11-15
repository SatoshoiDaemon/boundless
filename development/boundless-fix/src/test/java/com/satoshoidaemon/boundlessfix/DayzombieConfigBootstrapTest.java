package com.satoshoidaemon.boundlessfix;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DayzombieConfigBootstrapTest {
    @TempDir
    Path temporaryDirectory;

    @Test
    void copiesExistingJsonSettingsToTheExpectedExtensionlessPath() throws Exception {
        Path configDirectory = Files.createDirectory(temporaryDirectory.resolve("config"));
        String settings = "{\"Day zombie spawn rate\": 10}";
        Files.writeString(configDirectory.resolve("dayzombiesconfig.json"), settings);

        boolean created = DayzombieConfigBootstrap.createIfMissing(configDirectory, () -> {
            throw new AssertionError("The bundled default must not replace a user config.");
        });

        assertTrue(created);
        assertEquals(settings, Files.readString(configDirectory.resolve("dayzombiesconfig")));
    }

    @Test
    void doesNotOverwriteAnExistingExtensionlessConfig() throws Exception {
        Path configDirectory = Files.createDirectory(temporaryDirectory.resolve("config"));
        Path expected = Files.writeString(configDirectory.resolve("dayzombiesconfig"), "user settings");
        Files.writeString(configDirectory.resolve("dayzombiesconfig.json"), "stale settings");

        boolean created = DayzombieConfigBootstrap.createIfMissing(configDirectory, () -> {
            throw new AssertionError("The bundled default must not be opened.");
        });

        assertFalse(created);
        assertEquals("user settings", Files.readString(expected));
    }

    @Test
    void usesBundledDefaultWhenNeitherConfigFileExists() throws Exception {
        Path configDirectory = temporaryDirectory.resolve("config");
        byte[] settings = "bundled settings".getBytes(StandardCharsets.UTF_8);

        boolean created = DayzombieConfigBootstrap.createIfMissing(
                configDirectory,
                () -> new ByteArrayInputStream(settings));

        assertTrue(created);
        assertEquals("bundled settings", Files.readString(configDirectory.resolve("dayzombiesconfig")));
    }

    @Test
    void reportsAMissingBundledDefaultWithoutCreatingAnEmptyFile() {
        Path configDirectory = temporaryDirectory.resolve("config");

        assertThrows(IOException.class,
                () -> DayzombieConfigBootstrap.createIfMissing(configDirectory, () -> (InputStream) null));
        assertFalse(Files.exists(configDirectory.resolve("dayzombiesconfig")));
    }
}
