package com.satoshoidaemon.boundlesstweaks.diagnostics;

import java.util.Arrays;

/** Keeps the latest 1,200 server tick durations for on-demand percentile reporting. */
public final class TickWindow {
    public static final int CAPACITY = 1_200;

    private static final long[] START_TIMES_NS = new long[CAPACITY];
    private static final long[] DURATIONS_NS = new long[CAPACITY];
    private static int nextIndex;
    private static int sampleCount;

    private TickWindow() {
    }

    public static synchronized void record(long startTimeNs, long durationNs) {
        if (durationNs <= 0) {
            return;
        }
        START_TIMES_NS[nextIndex] = startTimeNs;
        DURATIONS_NS[nextIndex] = durationNs;
        nextIndex = (nextIndex + 1) % CAPACITY;
        sampleCount = Math.min(sampleCount + 1, CAPACITY);
    }

    public static synchronized void reset() {
        nextIndex = 0;
        sampleCount = 0;
        Arrays.fill(START_TIMES_NS, 0L);
        Arrays.fill(DURATIONS_NS, 0L);
    }

    public static synchronized Snapshot snapshot() {
        if (sampleCount == 0) {
            return new Snapshot(new long[0], 0.0);
        }

        long[] durations = new long[sampleCount];
        int oldestIndex = (nextIndex - sampleCount + CAPACITY) % CAPACITY;
        long oldestStart = START_TIMES_NS[oldestIndex];
        long newestIndex = (nextIndex - 1 + CAPACITY) % CAPACITY;
        long newestEnd = START_TIMES_NS[(int) newestIndex] + DURATIONS_NS[(int) newestIndex];

        for (int i = 0; i < sampleCount; i++) {
            int sourceIndex = (oldestIndex + i) % CAPACITY;
            durations[i] = DURATIONS_NS[sourceIndex];
        }

        double spanSeconds = Math.max(0.0, (newestEnd - oldestStart) / 1_000_000_000.0);
        return new Snapshot(durations, spanSeconds);
    }

    public static final class Snapshot {
        private final long[] durationsNs;
        private final double spanSeconds;

        private Snapshot(long[] durationsNs, double spanSeconds) {
            this.durationsNs = durationsNs;
            this.spanSeconds = spanSeconds;
        }

        public int sampleCount() {
            return durationsNs.length;
        }

        public double spanSeconds() {
            return spanSeconds;
        }

        public double meanMs() {
            if (durationsNs.length == 0) {
                return 0.0;
            }
            long total = 0L;
            for (long duration : durationsNs) {
                total += duration;
            }
            return total / (double) durationsNs.length / 1_000_000.0;
        }

        public double percentileMs(double percentile) {
            if (durationsNs.length == 0) {
                return 0.0;
            }
            long[] sorted = durationsNs.clone();
            Arrays.sort(sorted);
            int index = (int) Math.ceil(percentile * sorted.length) - 1;
            index = Math.max(0, Math.min(index, sorted.length - 1));
            return sorted[index] / 1_000_000.0;
        }

        public double minMs() {
            if (durationsNs.length == 0) {
                return 0.0;
            }
            long minimum = Long.MAX_VALUE;
            for (long duration : durationsNs) {
                minimum = Math.min(minimum, duration);
            }
            return minimum / 1_000_000.0;
        }

        public double maxMs() {
            if (durationsNs.length == 0) {
                return 0.0;
            }
            long maximum = Long.MIN_VALUE;
            for (long duration : durationsNs) {
                maximum = Math.max(maximum, duration);
            }
            return maximum / 1_000_000.0;
        }
    }
}
