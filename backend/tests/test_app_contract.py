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


async def fake_llm_response(prompt: str, max_tokens: int = 1024) -> str:
    return "test conclusion"


class AppContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = load_backend_module()
        transport = httpx.ASGITransport(app=self.backend.app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        self.llm_patch = patch.object(self.backend, "call_zhipu_llm", side_effect=fake_llm_response)
        self.llm_mock = self.llm_patch.start()

    async def asyncTearDown(self):
        self.llm_patch.stop()
        await self.client.aclose()

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
        self.assertIn("bucketed", llm_prompt.lower())
        self.assertNotIn("75.5", llm_prompt)
        self.assertNotIn(f"{report['fall_risk']['probability']:.1%}", llm_prompt)


if __name__ == "__main__":
    unittest.main()
