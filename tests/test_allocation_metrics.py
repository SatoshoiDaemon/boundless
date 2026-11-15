from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from scripts.analyze_perf_capture import JfrAllocationMetrics


class JfrAllocationMetricsTests(unittest.TestCase):
    def test_reports_sampled_classes_and_first_application_frame(self) -> None:
        metrics = JfrAllocationMetrics()
        timestamp = datetime(2026, 11, 14, tzinfo=timezone.utc)
        metrics.add(
            "jdk.ObjectAllocationSample",
            {
                "objectClass": {"name": "[B"},
                "stackTrace": {
                    "frames": [
                        {"method": {"type": {"name": "java/lang/Object"}, "name": "<init>"}},
                        {"method": {"type": {"name": "example/BoundlessTicker"}, "name": "tick"}},
                    ]
                },
            },
            timestamp,
        )

        summary = metrics.summary()

        self.assertEqual(1, summary["objectAllocationSampleCount"])
        self.assertEqual(
            [{"class": "[B", "sampleCount": 1}],
            summary["mostSampledObjectClasses"],
        )
        self.assertEqual(
            [{"site": "example/BoundlessTicker.tick", "sampleCount": 1}],
            summary["mostSampledAllocationSites"],
        )

    def test_computes_per_thread_counter_delta_and_rate(self) -> None:
        metrics = JfrAllocationMetrics()
        start = datetime(2026, 11, 14, tzinfo=timezone.utc)
        thread = {"javaThreadId": 42, "javaName": "Server thread"}
        metrics.add(
            "jdk.ThreadAllocationStatistics",
            {"allocated": 100, "thread": thread},
            start,
        )
        metrics.add(
            "jdk.ThreadAllocationStatistics",
            {"allocated": 1_048_676, "thread": thread},
            start + timedelta(seconds=20),
        )

        counters = metrics.summary()["threadAllocationCounters"]

        self.assertEqual(1, counters["threadIntervalCount"])
        self.assertEqual(1_048_576, counters["observedAllocatedBytes"])
        self.assertEqual(1_048_576, counters["mostAllocatedThreads"][0]["allocatedBytes"])
        self.assertAlmostEqual(0.05, counters["mostAllocatedThreads"][0]["allocatedMiBPerSecond"])


if __name__ == "__main__":
    unittest.main()
