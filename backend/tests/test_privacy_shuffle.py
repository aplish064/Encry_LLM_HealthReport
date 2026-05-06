import random
import unittest

from backend.privacy_shuffle import (
    build_anonymous_database,
    build_distribution_summary,
    build_display_candidates,
    build_protected_llm_summary,
    build_real_data_record,
    derive_privacy_profile,
    generate_synthetic_database,
    generate_synthetic_candidate_pool,
    select_protected_candidate,
)


class PrivacyShuffleTests(unittest.TestCase):
    def setUp(self):
        self.raw_results = [
            {"model": "ECG Arrhythmia", "model_id": "ecg", "input_modality": "WiFi CSI", "tool": "secure_ecg_toolbox", "score": 75.5, "status": "normal"},
            {"model": "Blood Pressure", "model_id": "bp", "input_modality": "UWB Radar", "tool": "secure_bp_toolbox", "score": 142.0, "status": "elevated"},
            {"model": "Sleep Staging", "model_id": "sleep", "input_modality": "Depth Camera", "tool": "secure_sleep_toolbox", "score": 68.0, "status": "low"},
            {"model": "Metabolic Score", "model_id": "metabolic", "input_modality": "IMU Sensor", "tool": "secure_metabolic_toolbox", "score": 52.0, "status": "normal"},
            {"model": "Risk Assessment", "model_id": "risk", "input_modality": "RGB Camera", "tool": "secure_risk_toolbox", "score": 0.41, "status": "moderate"},
        ]
        self.raw_report = {
            "overall": "Watch",
            "fall_risk": {
                "level": "Moderate",
                "probability": 0.41,
                "drivers": ["BP elevated", "Sleep reduced"],
            },
            "metrics": [
                {"name": "Heart Rate", "value": 76, "unit": "bpm", "ref": "60-100", "status": "normal"},
                {"name": "Respiratory Rate", "value": 17, "unit": "rpm", "ref": "12-20", "status": "normal"},
                {"name": "Blood Pressure", "value": 142, "unit": "mmHg", "ref": "<120", "status": "high"},
                {"name": "SpO2", "value": 97, "unit": "%", "ref": "95-100", "status": "normal"},
                {"name": "Sleep Efficiency", "value": 68, "unit": "%", "ref": ">85", "status": "low"},
                {"name": "Cadence", "value": 91, "unit": "spm", "ref": "90-120", "status": "normal"},
            ],
            "recommendations": ["Reduce sodium intake", "Improve sleep hygiene"],
            "narrative": "Overall status: Watch.",
            "charts": {
                "activity_mix": {"labels": ["Walk", "Stand", "Sit", "Sleep"], "values": [0.21, 0.18, 0.24, 0.37]},
                "radar": {"labels": ["Cardio", "BP", "Sleep", "Metabolic", "Recovery", "Safety"], "values": [68, 54, 51, 62, 58, 60]},
                "vitals": {"labels": ["HR", "RR", "BP", "SpO2"], "values": [76, 17, 142, 97], "refs": [80, 16, 120, 98]},
                "sparklines": {},
            },
            "disclaimer": "Demo output only — not for medical use.",
        }

    def test_derive_privacy_profile_returns_bucketed_fields(self):
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        self.assertEqual(profile["overall"], "Watch")
        self.assertEqual(profile["risk_level"], "Moderate")
        self.assertIn("metric_buckets", profile)

    def test_build_real_data_record_keeps_precise_backend_values(self):
        record = build_real_data_record(self.raw_results, self.raw_report)

        self.assertEqual(record["kind"], "real")
        self.assertEqual(record["model_outputs"][0]["score"], 75.5)
        self.assertEqual(record["derived_metrics"]["fall_probability"], 0.41)
        self.assertEqual(record["derived_metrics"]["heart_rate"], 76)
        self.assertEqual(record["derived_metrics"]["blood_pressure"], 142)
        self.assertIn("activity_mix", record["derived_metrics"])

    def test_generate_synthetic_database_returns_valid_fake_records(self):
        rng = random.Random(123)
        real_record = build_real_data_record(self.raw_results, self.raw_report)

        records = generate_synthetic_database(real_record, database_size=8, rng=rng)

        self.assertEqual(len(records), 8)
        self.assertTrue(all(record["kind"] == "synthetic" for record in records))
        for record in records:
            metrics = record["derived_metrics"]
            self.assertGreaterEqual(metrics["heart_rate"], 45)
            self.assertLessEqual(metrics["heart_rate"], 130)
            self.assertGreaterEqual(metrics["respiratory_rate"], 8)
            self.assertLessEqual(metrics["respiratory_rate"], 30)
            self.assertGreaterEqual(metrics["blood_pressure"], 90)
            self.assertLessEqual(metrics["blood_pressure"], 180)
            self.assertGreaterEqual(metrics["fall_probability"], 0.05)
            self.assertLessEqual(metrics["fall_probability"], 0.95)
            self.assertAlmostEqual(sum(metrics["activity_mix"]["values"]), 1.0, places=3)

    def test_generate_synthetic_database_supports_100_record_distribution(self):
        rng = random.Random(123)
        real_record = build_real_data_record(self.raw_results, self.raw_report)

        records = generate_synthetic_database(real_record, database_size=100, rng=rng)

        self.assertEqual(len(records), 100)
        self.assertTrue(all(record["kind"] == "synthetic" for record in records))

    def test_build_anonymous_database_hides_real_record_but_selects_it_by_token(self):
        real_record = build_real_data_record(self.raw_results, self.raw_report)
        fake_records = generate_synthetic_database(real_record, database_size=8, rng=random.Random(7))

        bundle = build_anonymous_database(real_record, fake_records, rng=random.Random(7))

        self.assertEqual(bundle["selected_record"]["kind"], "real")
        self.assertEqual(
            bundle["selected_record_label"],
            bundle["shuffle_order_preview"][bundle["selected_record_index"]],
        )
        self.assertEqual(len(bundle["anonymous_database"]), 9)
        for preview in bundle["anonymous_database_preview"]:
            self.assertNotIn("kind", preview)
            self.assertNotIn("is_real", preview)
            self.assertNotIn("_selection_token", preview)
            self.assertTrue(preview["label"].startswith("Synthetic Record"))

    def test_distribution_summary_describes_101_records_without_exposing_internals(self):
        real_record = build_real_data_record(self.raw_results, self.raw_report)
        fake_records = generate_synthetic_database(real_record, database_size=100, rng=random.Random(7))
        bundle = build_anonymous_database(real_record, fake_records, rng=random.Random(7))

        summary = build_distribution_summary(bundle)

        self.assertEqual(summary["synthetic_record_count"], 100)
        self.assertEqual(summary["database_size"], 101)
        self.assertEqual(
            sum(bucket["count"] for bucket in summary["risk_buckets"]),
            101,
        )
        self.assertGreaterEqual(len(summary["scatter_points"]), 24)
        self.assertEqual(summary["target_point"]["label"], bundle["selected_record_label"])
        self.assertEqual(summary["token_flow"]["visibility"], "backend_only")
        self.assertIn("H(session_seed, real_id, nonce)", summary["token_flow"]["generation"])
        self.assertIn("token_map[token]", summary["token_flow"]["lookup"])
        self.assertNotIn("_selection_token", str(summary))
        self.assertNotIn("is_real", str(summary))
        self.assertNotIn("kind", str(summary["scatter_points"]))

    def test_build_protected_llm_summary_uses_buckets_not_precise_values(self):
        real_record = build_real_data_record(self.raw_results, self.raw_report)
        real_record["_anonymous_label"] = "Synthetic Record 07"

        summary = build_protected_llm_summary(real_record)

        self.assertEqual(summary["record"], "Synthetic Record 07")
        self.assertEqual(summary["risk_profile"]["fall_probability_bucket"], "40-45%")
        self.assertEqual(summary["metrics"]["blood_pressure"], "elevated")
        self.assertEqual(summary["metrics"]["heart_rate"], "normal range")
        self.assertEqual(summary["model_results"][0]["score_bucket"], "75-80")
        self.assertNotIn("75.5", str(summary))
        self.assertNotIn("142.0", str(summary))

    def test_generate_candidate_pool_returns_requested_size(self):
        rng = random.Random(42)
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        pool = generate_synthetic_candidate_pool(profile, self.raw_results, self.raw_report, pool_size=10, rng=rng)
        self.assertEqual(len(pool), 10)

    def test_select_protected_candidate_returns_single_candidate_after_shuffle(self):
        rng = random.Random(42)
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        pool = generate_synthetic_candidate_pool(profile, self.raw_results, self.raw_report, pool_size=10, rng=rng)
        protected = select_protected_candidate(pool, rng=rng)
        self.assertIn("results", protected)
        self.assertIn("report", protected)

    def test_select_protected_candidate_records_random_visible_order_index(self):
        pool = [
            {"label": "Candidate A", "results": [], "report": {}},
            {"label": "Candidate B", "results": [], "report": {}},
            {"label": "Candidate C", "results": [], "report": {}},
            {"label": "Candidate D", "results": [], "report": {}},
        ]
        expected_rng = random.Random(7)
        expected_order = list(pool)
        expected_rng.shuffle(expected_order)
        expected_index = expected_rng.randrange(len(expected_order))

        protected = select_protected_candidate(pool, rng=random.Random(7))

        self.assertEqual(
            protected["_shuffle_order_preview"],
            [candidate["label"] for candidate in expected_order],
        )
        self.assertEqual(protected["_selected_order_index"], expected_index)
        self.assertEqual(protected["_source_label"], expected_order[expected_index]["label"])

    def test_build_display_candidates_limits_frontend_exposure(self):
        rng = random.Random(42)
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        pool = generate_synthetic_candidate_pool(profile, self.raw_results, self.raw_report, pool_size=10, rng=rng)
        cards = build_display_candidates(pool, limit=4)
        self.assertEqual(len(cards), 4)
        self.assertIn("metric_summary", cards[0])
        self.assertNotIn("results", cards[0])


if __name__ == "__main__":
    unittest.main()
