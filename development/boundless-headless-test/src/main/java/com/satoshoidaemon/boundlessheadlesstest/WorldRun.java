package com.satoshoidaemon.boundlessheadlesstest;

import com.google.gson.GsonBuilder;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraftforge.fml.loading.FMLPaths;
import org.slf4j.Logger;
import com.mojang.logging.LogUtils;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class WorldRun {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Pattern PREDICTION = Pattern.compile(
            "\\\"enablePrediction\\\"\\s*:\\s*\\{(?:(?:\\s*//[^\\n]*\\n)|(?:\\s*/\\*.*?\\*/)|\\s)*\\\"enablePrediction\\\"\\s*:\\s*(true|false)",
            Pattern.DOTALL);
    private static final List<TickSample> TICKS = new ArrayList<>();
    private static final List<MemorySample> MEMORY = new ArrayList<>();

    private static volatile boolean active;
    private static volatile boolean seedApplied;
    private static int requestedTicks;
    private static int sampledTicks;
    private static long startNanos;
    private static long previousTickNanos;
    private static long serverTickStartNanos;
    private static long startServerTick;
    private static String actualSeed = "unknown";
    private static boolean betterChunkLoadingLoaded;
    private static Boolean predictionEnabled;
    private static int modCount;
    private static double startX = Double.NaN;
    private static double startZ = Double.NaN;
    private static double endX = Double.NaN;
    private static double endZ = Double.NaN;
    private static Map<String, Object> report = Map.of();

    private WorldRun() {}

    static String seedText() {
        return System.getProperty("boundless.headless.seed", "4242424242");
    }

    static int requestedTicks() {
        return Math.max(200, Integer.getInteger("boundless.headless.ticks", 1200));
    }

    static boolean seedWasApplied() {
        return seedApplied;
    }

    static void markSeedApplied(boolean applied) {
        seedApplied = applied;
    }

    static synchronized void begin(ServerLevel level, long serverTick, boolean bclLoaded, int loadedMods) {
        if (active) {
            return;
        }
        TICKS.clear();
        MEMORY.clear();
        report = Map.of();
        requestedTicks = requestedTicks();
        sampledTicks = 0;
        startNanos = System.nanoTime();
        previousTickNanos = startNanos;
        serverTickStartNanos = startNanos;
        startServerTick = serverTick;
        actualSeed = Long.toString(level.getSeed());
        betterChunkLoadingLoaded = bclLoaded;
        predictionEnabled = readPredictionSetting();
        modCount = loadedMods;
        startX = Double.NaN;
        startZ = Double.NaN;
        endX = Double.NaN;
        endZ = Double.NaN;
        active = true;
    }

    static boolean isActive() {
        return active;
    }

    static boolean shouldMove() {
        return active && sampledTicks < requestedTicks;
    }

    static synchronized void recordPosition(double x, double z) {
        if (!active) {
            return;
        }
        if (Double.isNaN(startX)) {
            startX = x;
            startZ = z;
        }
        endX = x;
        endZ = z;
        sampledTicks++;
    }

    static synchronized void startServerTick() {
        if (active) {
            serverTickStartNanos = System.nanoTime();
        }
    }

    static synchronized void recordServerTick() {
        if (!active) {
            return;
        }
        long now = System.nanoTime();
        long elapsedNanos = now - startNanos;
        long intervalNanos = now - previousTickNanos;
        long workNanos = now - serverTickStartNanos;
        previousTickNanos = now;
        TICKS.add(new TickSample(TICKS.size() + 1, elapsedNanos / 1_000_000.0,
                intervalNanos / 1_000_000.0, workNanos / 1_000_000.0));

        if (TICKS.size() % 20 == 0) {
            MEMORY.add(memorySample(TICKS.size(), elapsedNanos));
        }
    }

    static synchronized void finish(long endServerTick) throws IOException {
        if (!active) {
            return;
        }
        active = false;
        Path logs = FMLPaths.GAMEDIR.get().resolve("logs");
        Files.createDirectories(logs);

        Path tickCsv = logs.resolve("headless-world-ticks.csv");
        StringBuilder tickText = new StringBuilder("tick,elapsed_ms,tick_interval_ms,tick_work_ms\n");
        for (TickSample tick : TICKS) {
            tickText.append(tick.tick()).append(',')
                    .append(tick.elapsedMs()).append(',')
                    .append(tick.intervalMs()).append(',')
                    .append(tick.workMs()).append('\n');
        }
        Files.writeString(tickCsv, tickText);

        Path memoryCsv = logs.resolve("headless-world-memory.csv");
        StringBuilder memoryText = new StringBuilder(
                "tick,elapsed_ms,heap_used_mb,heap_committed_mb,host_free_memory_mb,process_cpu_load_pct\n");
        for (MemorySample sample : MEMORY) {
            memoryText.append(sample.tick()).append(',')
                    .append(sample.elapsedMs()).append(',')
                    .append(sample.heapUsedMb()).append(',')
                    .append(sample.heapCommittedMb()).append(',')
                    .append(sample.hostFreeMb()).append(',')
                    .append(sample.processCpuLoadPct()).append('\n');
        }
        Files.writeString(memoryCsv, memoryText);

        double travel = Double.isNaN(startX) || Double.isNaN(endX) ? 0.0
                : Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endZ - startZ, 2));
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("runner_benchmark", "GitHub Actions ubuntu-latest / Linux; not comparable to Windows hardware");
        values.put("condition", System.getProperty("boundless.headless.condition", "world"));
        values.put("created_at_utc", Instant.now().toString());
        values.put("minecraft_version", "1.20.1");
        values.put("forge_version", BoundlessHeadlessTest.forgeVersion());
        values.put("seed", actualSeed);
        values.put("expected_seed", seedText());
        values.put("seed_field_applied", seedApplied);
        values.put("better_chunk_loading_loaded", betterChunkLoadingLoaded);
        values.put("enable_prediction", predictionEnabled);
        values.put("tick_work_metrics_file", tickCsv.getFileName().toString());
        values.put("loaded_mod_count", modCount);
        values.put("requested_ticks", requestedTicks);
        values.put("client_movement_ticks", sampledTicks);
        values.put("server_ticks_sampled", TICKS.size());
        values.put("server_tick_count_delta", endServerTick - startServerTick);
        values.put("elapsed_seconds", (System.nanoTime() - startNanos) / 1_000_000_000.0);
        values.put("player_start_x", finiteOrNull(startX));
        values.put("player_start_z", finiteOrNull(startZ));
        values.put("player_end_x", finiteOrNull(endX));
        values.put("player_end_z", finiteOrNull(endZ));
        values.put("player_travel_blocks", travel);
        values.put("movement_workload_valid", travel >= 8.0);
        values.put("tick_metrics_file", tickCsv.getFileName().toString());
        values.put("memory_metrics_file", memoryCsv.getFileName().toString());
        report = values;
        Files.writeString(logs.resolve("headless-world-report.json"),
                new GsonBuilder().setPrettyPrinting().create().toJson(values) + System.lineSeparator());
    }

    static synchronized String resultJson() {
        return new GsonBuilder().setPrettyPrinting().create().toJson(report);
    }

    static Boolean predictionConfigured() {
        return predictionEnabled;
    }

    private static MemorySample memorySample(int tick, long elapsedNanos) {
        Runtime runtime = Runtime.getRuntime();
        double heapUsed = (runtime.totalMemory() - runtime.freeMemory()) / 1024.0 / 1024.0;
        double heapCommitted = runtime.totalMemory() / 1024.0 / 1024.0;
        double freePhysicalMb = Double.NaN;
        double cpuLoadPct = Double.NaN;
        java.lang.management.OperatingSystemMXBean bean = ManagementFactory.getOperatingSystemMXBean();
        if (bean instanceof com.sun.management.OperatingSystemMXBean osBean) {
            freePhysicalMb = osBean.getFreeMemorySize() / 1024.0 / 1024.0;
            double load = osBean.getProcessCpuLoad();
            if (load >= 0) {
                cpuLoadPct = load * 100.0;
            }
        }
        return new MemorySample(tick, elapsedNanos / 1_000_000.0, heapUsed,
                heapCommitted, freePhysicalMb, cpuLoadPct);
    }

    private static Boolean readPredictionSetting() {
        Path config = FMLPaths.CONFIGDIR.get().resolve("betterchunkloading.json");
        try {
            Matcher matcher = PREDICTION.matcher(Files.readString(config));
            if (matcher.find()) {
                return Boolean.parseBoolean(matcher.group(1));
            }
        } catch (IOException exception) {
            LOGGER.warn("Could not read Better Chunk Loading config at {}", config, exception);
        }
        return null;
    }

    private static Object finiteOrNull(double value) {
        return Double.isFinite(value) ? value : null;
    }

    private record TickSample(int tick, double elapsedMs, double intervalMs, double workMs) {}
    private record MemorySample(int tick, double elapsedMs, double heapUsedMb,
                                double heapCommittedMb, double hostFreeMb,
                                double processCpuLoadPct) {}
}
