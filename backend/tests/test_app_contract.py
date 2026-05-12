import csv
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_backend_module():
    app_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("backend_app_module", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


async def fake_llm_response(prompt: str, provider: str = None, max_tokens: int = 1024) -> str:
    return "test conclusion"


class AppContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = load_backend_module()
        transport = httpx.ASGITransport(app=self.backend.app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        self.llm_patch = patch.object(self.backend, "call_selected_llm", side_effect=fake_llm_response)
        self.llm_mock = self.llm_patch.start()

    async def asyncTearDown(self):
        self.llm_patch.stop()
        await self.client.aclose()

    async def test_all_llm_provider_choices_route_to_xiaomi_mimo(self):
        providers = ["qwen", "deepseek", "zhipu", "kimi", "minimax", "doubao", "xiaomi-mimo", "unknown"]

        for provider in providers:
            with self.subTest(provider=provider):
                self.assertEqual(self.backend.normalize_llm_provider(provider), "xiaomi-mimo")

    async def test_xiaomi_mimo_default_endpoint_is_configured(self):
        config = self.backend.LLM_PROVIDER_OPTIONS["xiaomi-mimo"]

        self.assertEqual(config["default_base_url"], "https://api.xiaomimimo.com/v1/chat/completions")
        self.assertTrue(config["default_api_key"].startswith("sk-"))
        self.assertEqual(config["default_model"], "mimo-v2-flash")

    async def test_cycle_accepts_modality_ids_without_falling_back_to_all_modalities(self):
        response = await self.client.get("/api/cycle", params={"selected_modalities": "depth,uwb,imu,csi,rgb"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        enabled_modalities = payload["step1"]["enabled_modalities"]
        self.assertEqual(
            enabled_modalities,
            ["Depth Camera", "UWB Radar", "IMU Sensor", "WiFi CSI", "RGB Camera"],
        )

    async def test_cycle_preserves_core_response_shape(self):
        response = await self.client.get("/api/cycle", params={"selected_modalities": "depth,uwb,imu,csi,rgb"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema"], "he-multimodal-cycle/v1")
        self.assertIn("step1", payload)
        self.assertIn("step2", payload)
        self.assertIn("step3", payload)
        self.assertIsInstance(payload["step3"]["report_conclusion"], str)
        self.assertIn("report", payload["step3"])
        self.assertIsInstance(payload["step3"].get("plaintext_prompt"), str)

    async def test_cycle_returns_privacy_protection_block(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        privacy = payload.get("privacy_protection")

        self.assertIsInstance(privacy, dict)
        self.assertTrue(privacy.get("enabled"))
        self.assertEqual(privacy.get("method"), "synthetic_database_shuffle")
        self.assertIsInstance(privacy.get("database_size"), int)
        self.assertEqual(privacy.get("synthetic_record_count"), 100)
        self.assertEqual(privacy.get("database_size"), 101)
        self.assertIsInstance(privacy.get("distribution_summary"), dict)
        self.assertIsInstance(privacy.get("token_flow"), dict)
        self.assertEqual(privacy.get("token_flow", {}).get("visibility"), "backend_only")
        self.assertIsInstance(privacy.get("anonymous_database_preview"), list)
        self.assertGreaterEqual(len(privacy.get("anonymous_database_preview", [])), 3)
        self.assertIsInstance(privacy.get("shuffle_order_preview"), list)
        self.assertIsInstance(privacy.get("selected_record_label"), str)
        self.assertIsInstance(privacy.get("selected_record_index"), int)
        self.assertGreaterEqual(privacy.get("selected_record_index"), 0)
        self.assertLess(privacy.get("selected_record_index"), len(privacy.get("shuffle_order_preview", [])))
        self.assertIn(privacy.get("selected_record_label"), privacy.get("shuffle_order_preview", []))
        self.assertEqual(privacy.get("llm_summary_mode"), "bucketed_non_trusted")
        self.assertIsInstance(privacy.get("protected_llm_summary_preview"), dict)
        self.assertIsInstance(privacy.get("generation_policy"), dict)
        self.assertIsInstance(privacy.get("summary"), str)
        self.assertNotIn("_selection_token", str(privacy))
        self.assertNotIn("is_real", str(privacy))
        self.assertNotIn('"kind"', str(privacy.get("distribution_summary", {})))

    async def test_privacy_shuffle_returns_plaintext_prompt_for_stage(self):
        dispatch = await self.client.get(
            "/api/dispatch",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(dispatch.status_code, 200)
        session_id = dispatch.json()["session_id"]

        response = await self.client.get(
            "/api/privacy_shuffle",
            params={"session_id": session_id},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("privacy_protection", payload)
        self.assertIsInstance(payload.get("privacy_protection"), dict)
        self.assertIn("plaintext_prompt", payload)
        self.assertIsInstance(payload.get("plaintext_prompt"), str)
        self.assertIn("bucketed", payload["plaintext_prompt"].lower())

    async def test_cycle_keeps_precise_dashboard_report_and_results(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        privacy = payload["privacy_protection"]
        report = payload["step3"]["report"]
        results = payload["step3"]["results"]

        self.assertEqual(privacy["llm_summary_mode"], "bucketed_non_trusted")
        self.assertIsInstance(report.get("overall"), str)
        self.assertIsInstance(report.get("metrics"), list)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["score"], 75.5)
        self.assertIsInstance(report["fall_risk"]["probability"], float)
        self.assertNotEqual(privacy["protected_llm_summary_preview"]["model_results"][0]["score_bucket"], "75.5")
        llm_prompt = self.llm_mock.call_args.args[0]
        self.assertIn("Section summary", llm_prompt)
        self.assertIn("Mobility & Fall Stability", llm_prompt)
        self.assertIn("bucketed", llm_prompt.lower())
        self.assertNotIn(str(report["summary"]["health_index"]), llm_prompt)
        self.assertNotIn("75.5", llm_prompt)
        self.assertNotIn(f"{report['fall_risk']['probability']:.1%}", llm_prompt)

    async def test_modalities_defaults_to_healthcare(self):
        response = await self.client.get("/api/modalities")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "healthcare")
        modality_ids = [item["id"] for item in payload["modalities"]]
        self.assertIn("depth", modality_ids)
        self.assertIn("uwb", modality_ids)
        self.assertIn("blood", modality_ids)

    async def test_modalities_returns_finance_cards_for_finance_scenario(self):
        response = await self.client.get("/api/modalities", params={"scenario": "finance"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "finance")
        self.assertEqual(
            [item["id"] for item in payload["modalities"]],
            ["income", "expenses", "savings", "loan", "credit", "profile"],
        )
        self.assertEqual(payload["modalities"][0]["name"], "Income")
        self.assertEqual(payload["modalities"][4]["name"], "Credit")

    async def test_modalities_rejects_unknown_explicit_scenario(self):
        response = await self.client.get("/api/modalities", params={"scenario": "unknown"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertIn("Unsupported scenario", payload["error"])

    async def test_finance_dispatch_returns_finance_session_and_models(self):
        response = await self.client.get(
            "/api/dispatch",
            params={"scenario": "finance", "selected_modalities": "income,credit,loan"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "finance")
        self.assertEqual(payload.get("data_source"), "synthetic_personal_finance_dataset.csv")
        self.assertIn("session_id", payload)
        self.assertEqual(payload["step1"]["enabled_modalities"], ["Income", "Credit", "Loan"])
        self.assertEqual(
            [item["id"] for item in payload["step2"]["cluster_models"]],
            [
                "income_capacity",
                "expense_burden",
                "savings_resilience",
                "loan_stress",
                "credit_risk",
                "profile_context",
            ],
        )
        self.assertEqual(
            [item["model_id"] for item in payload["step2"]["assignments"]],
            ["income_capacity", "loan_stress", "credit_risk"],
        )
        self.assertEqual(
            [item["model_id"] for item in payload["raw_results"]],
            ["income_capacity", "loan_stress", "credit_risk"],
        )

    async def test_finance_dispatch_rejects_missing_finance_dataset_fields(self):
        with patch.object(self.backend, "load_finance_records", return_value=[{"user_id": "U1"}]):
            response = await self.client.get(
                "/api/dispatch",
                params={"scenario": "finance", "selected_modalities": "income"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertIn("Missing finance dataset fields", payload["error"])

    async def test_finance_expense_burden_caps_score_at_100(self):
        result = self.backend.finance_score_for_model(
            "expense_burden",
            {"monthly_income_usd": "1000", "monthly_expenses_usd": "2500"},
        )

        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["status"], "attention")

    async def test_finance_expense_burden_treats_zero_income_positive_expenses_as_high_risk(self):
        result = self.backend.finance_score_for_model(
            "expense_burden",
            {"monthly_income_usd": "0", "monthly_expenses_usd": "500"},
        )

        self.assertGreaterEqual(result["score"], 70)
        self.assertNotEqual(result["status"], "stable")

    async def test_finance_loan_stress_treats_zero_income_positive_emi_as_high_risk(self):
        result = self.backend.finance_score_for_model(
            "loan_stress",
            {
                "monthly_income_usd": "0",
                "monthly_emi_usd": "100",
                "debt_to_income_ratio": "0",
                "loan_interest_rate_pct": "0",
            },
        )

        self.assertGreaterEqual(result["score"], 70)
        self.assertNotEqual(result["status"], "stable")

    async def test_finance_report_uses_finance_domain_prompt_and_report(self):
        finance_record = {
            "user_id": "U-privacy",
            "age": "47",
            "gender": "female",
            "education_level": "masters",
            "employment_status": "employed",
            "job_title": "Analyst",
            "monthly_income_usd": "12345",
            "monthly_expenses_usd": "6789",
            "savings_usd": "43210",
            "has_loan": "yes",
            "loan_type": "personal",
            "loan_amount_usd": "98765",
            "loan_term_months": "37",
            "monthly_emi_usd": "1234",
            "loan_interest_rate_pct": "8.75",
            "debt_to_income_ratio": "1.37",
            "credit_score": "543",
            "savings_to_income_ratio": "3.5",
            "region": "west",
            "record_date": "2026-05-01",
        }
        with patch.object(self.backend, "load_finance_records", return_value=[finance_record]):
            dispatch = await self.client.get(
                "/api/dispatch",
                params={"scenario": "finance", "selected_modalities": "income,expenses,savings,loan,credit"},
            )
        self.assertEqual(dispatch.status_code, 200)
        session_id = dispatch.json()["session_id"]

        response = await self.client.get(
            "/api/report",
            params={"session_id": session_id, "llm_provider": "zhipu"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "finance")
        self.assertEqual(payload.get("data_source"), "synthetic_personal_finance_dataset.csv")
        report = payload["step3"]["report"]
        prompt = payload["step3"]["plaintext_prompt"]
        self.assertEqual(report.get("domain"), "finance")
        self.assertEqual(report.get("score_label"), "Financial resilience")
        self.assertIn("Financial Risk Summary", report["summary"]["title"])
        self.assertIn("personal finance risk analysis", prompt)
        self.assertNotIn("health", prompt.lower())
        self.assertNotIn("clinical", prompt.lower())
        self.assertNotIn("fall probability", prompt.lower())

        privacy = payload["privacy_protection"]
        distribution = privacy["distribution_summary"]
        self.assertEqual(
            distribution["axes"],
            {
                "x": "loan_stress_percentile",
                "y": "savings_resilience_percentile",
                "x_source": "loan_stress",
                "y_source": "savings_resilience",
            },
        )
        bucket_names = {item["bucket"] for item in distribution["risk_buckets"]}
        self.assertEqual(bucket_names, {"stable", "watch", "attention"})
        self.assertIn(distribution["target_point"]["bucket"], bucket_names)
        for point in distribution["scatter_points"]:
            self.assertGreaterEqual(point["x"], 0.0)
            self.assertLessEqual(point["x"], 1.0)
            self.assertGreaterEqual(point["y"], 0.0)
            self.assertLessEqual(point["y"], 1.0)
        self.assertNotIn("fall_probability", str(distribution))
        self.assertNotIn("sleep_efficiency", str(distribution))

        exact_raw_values = [
            "12345",
            "6789",
            "43210",
            "98765",
            "1234",
            "543",
        ]
        exact_raw_values.extend(str(item["score"]) for item in payload["step3"]["results"])
        for value in exact_raw_values:
            self.assertNotIn(value, prompt)


class FinanceDatasetTests(unittest.TestCase):
    DATA_PATH = BACKEND_DIR.parent / "test_data" / "synthetic_personal_finance_dataset.csv"

    def test_finance_dataset_exists_with_expected_shape(self):
        self.assertTrue(self.DATA_PATH.exists(), f"Missing finance dataset: {self.DATA_PATH}")

        with self.DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            row_count = sum(1 for _ in reader)

        self.assertEqual(len(header), 20)
        self.assertEqual(row_count, 32424)

    def test_finance_dataset_contains_required_columns(self):
        required = {
            "user_id",
            "age",
            "gender",
            "education_level",
            "employment_status",
            "job_title",
            "monthly_income_usd",
            "monthly_expenses_usd",
            "savings_usd",
            "has_loan",
            "loan_type",
            "loan_amount_usd",
            "loan_term_months",
            "monthly_emi_usd",
            "loan_interest_rate_pct",
            "debt_to_income_ratio",
            "credit_score",
            "savings_to_income_ratio",
            "region",
            "record_date",
        }

        self.assertTrue(self.DATA_PATH.exists(), f"Missing finance dataset: {self.DATA_PATH}")
        with self.DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
            header = set(next(csv.reader(handle)))

        missing_columns = required - header
        self.assertEqual(missing_columns, set(), f"Missing finance dataset columns: {missing_columns}")


if __name__ == "__main__":
    unittest.main()
