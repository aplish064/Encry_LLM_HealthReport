import random
import unittest

from backend.privacy_shuffle import (
    build_display_candidates,
    derive_privacy_profile,
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
