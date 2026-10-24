import unittest
from datetime import datetime, timezone

from backend.app.analytics import build_analysis


class AnalysisTests(unittest.TestCase):
    def test_uses_latest_forecast_published_before_cutoff(self):
        cutoff = datetime(2025, 12, 31, 10, tzinfo=timezone.utc)
        actuals = [
            {"startTime": "2026-01-02T00:00:00Z", "generation": 100},
            {"startTime": "2026-01-02T00:30:00Z", "generation": 120},
        ]
        forecasts = [
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2025-12-31T09:00:00Z",
                "generation": 90,
            },
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": 110,
            },
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2025-12-31T10:30:00Z",
                "generation": 200,
            },
            {
                "startTime": "2026-01-01T23:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": 100,
            }
        ]

        result = build_analysis(
            actuals,
            forecasts,
            cutoff,
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

        self.assertEqual(result["points"][0]["forecastMw"], 110)
        self.assertEqual(result["points"][0]["actualMw"], 110)
        self.assertEqual(result["metrics"]["maeMw"], 0)
        self.assertEqual(result["metrics"]["pairedIntervals"], 1)
        self.assertEqual(result["metrics"]["expectedIntervals"], 24)

    def test_reports_missing_actuals_without_fabricating_metrics(self):
        cutoff = datetime(2025, 12, 31, 10, tzinfo=timezone.utc)
        forecasts = [
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": 110,
            }
        ]

        result = build_analysis(
            [],
            forecasts,
            cutoff,
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

        self.assertIsNone(result["metrics"]["maeMw"])
        self.assertEqual(result["metrics"]["coveragePercent"], 0)

    def test_does_not_compare_hourly_forecast_with_partial_actual_hour(self):
        cutoff = datetime(2025, 12, 31, 10, tzinfo=timezone.utc)
        actuals = [
            {"startTime": "2026-01-02T00:00:00Z", "generation": 100},
        ]
        forecasts = [
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": 110,
            }
        ]

        result = build_analysis(
            actuals,
            forecasts,
            cutoff,
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

        self.assertIsNone(result["points"][0]["actualMw"])
        self.assertEqual(result["metrics"]["pairedIntervals"], 0)


if __name__ == "__main__":
    unittest.main()
