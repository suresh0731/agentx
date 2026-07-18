"""Tests for OPS effectiveness metric evaluation."""

import unittest
from datetime import datetime, timezone

from agentx.layers.analytics.ops_metrics import (
    OPS_TEAM_SIZE,
    build_ops_metrics,
    compute_manual_effort_reduction,
    compute_repairs_mtd,
)

SAMPLE_ROLLUPS = {
    "overall_stp_rate": 96.8,
    "auto_repair_success_rate": 94.7,
    "auto_repair_healed_count": 312,
    "instructions_reviewed": 47,
    "exception_queue_count": 47,
}


class OpsMetricsTests(unittest.TestCase):
    def test_ops_team_size_is_fixed(self):
        metrics = build_ops_metrics(SAMPLE_ROLLUPS)
        team = next(m for m in metrics if m["key"] == "ops_team_coverage")
        self.assertEqual(team["value"], OPS_TEAM_SIZE)
        self.assertEqual(team["value"], 25)
        self.assertEqual(team["label"], "Active Operations Users")

    def test_repairs_mtd_is_stable_within_month(self):
        fixed = datetime(2026, 7, 15, tzinfo=timezone.utc)
        a = compute_repairs_mtd(SAMPLE_ROLLUPS, now=fixed)
        b = compute_repairs_mtd(SAMPLE_ROLLUPS, now=fixed.replace(day=20))
        self.assertEqual(a, b)
        self.assertGreaterEqual(a, 3_120)

    def test_repairs_mtd_reflects_good_performance(self):
        strong = {**SAMPLE_ROLLUPS, "auto_repair_success_rate": 98.0, "auto_repair_healed_count": 400}
        weak = {**SAMPLE_ROLLUPS, "auto_repair_success_rate": 85.0, "auto_repair_healed_count": 200}
        fixed = datetime(2026, 7, 1, tzinfo=timezone.utc)
        self.assertGreaterEqual(
            compute_repairs_mtd(strong, now=fixed),
            compute_repairs_mtd(weak, now=fixed),
        )

    def test_manual_effort_reduction_in_healthy_range(self):
        pct = compute_manual_effort_reduction(SAMPLE_ROLLUPS)
        self.assertGreaterEqual(pct, 58.0)
        self.assertLessEqual(pct, 72.0)

    def test_manual_effort_reduction_improves_with_learning_signal(self):
        low_reviews = {**SAMPLE_ROLLUPS, "instructions_reviewed": 10, "exception_queue_count": 60}
        high_reviews = {**SAMPLE_ROLLUPS, "instructions_reviewed": 75, "exception_queue_count": 20}
        self.assertGreater(
            compute_manual_effort_reduction(high_reviews),
            compute_manual_effort_reduction(low_reviews),
        )

    def test_build_ops_metrics_returns_three_cards(self):
        metrics = build_ops_metrics(SAMPLE_ROLLUPS, now=datetime(2026, 7, 18, tzinfo=timezone.utc))
        self.assertEqual(len(metrics), 3)
        keys = {m["key"] for m in metrics}
        self.assertEqual(keys, {"ops_team_coverage", "repairs_mtd", "manual_effort_reduction"})
        effort = next(m for m in metrics if m["key"] == "manual_effort_reduction")
        self.assertEqual(effort["unit"], "%")
        self.assertEqual(effort["label"], "Learning-Driven Effort Reduction")


if __name__ == "__main__":
    unittest.main()
