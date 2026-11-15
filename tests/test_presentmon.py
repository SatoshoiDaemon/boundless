from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_perf_capture import analyze_presentmon


class PresentMonAnalysisTests(unittest.TestCase):
    def test_reads_native_presentmon_lower_camel_case_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frametime.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Application", "msBetweenPresents", "msBetweenDisplayChange"])
                for _ in range(120):
                    writer.writerow(["java.exe", "16.6667", "16.6667"])

            summary = analyze_presentmon(path)

        self.assertEqual(120, summary["frameCount"])
        self.assertEqual("DisplayedTime/MsBetweenDisplayChange", summary["metricUsed"])
        self.assertAlmostEqual(60.0, summary["meanFps"], places=2)
        self.assertEqual(120, summary["displayChangeFrameCount"])


if __name__ == "__main__":
    unittest.main()
