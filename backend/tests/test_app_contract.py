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
        self.llm_patch.start()

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
        self.assertEqual(privacy.get("method"), "synthetic_shuffle")
        self.assertEqual(privacy.get("pool_size"), 10)
        self.assertIsInstance(privacy.get("display_candidates"), list)
        self.assertGreaterEqual(len(privacy.get("display_candidates", [])), 3)
        self.assertLessEqual(len(privacy.get("display_candidates", [])), 5)
        self.assertIsInstance(privacy.get("summary"), str)

    async def test_cycle_routes_display_report_through_protected_output(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        privacy = payload["privacy_protection"]
        report = payload["step3"]["report"]
        results = payload["step3"]["results"]

        self.assertEqual(privacy["selected_label"], "Protected Output")
        self.assertIsInstance(report.get("overall"), str)
        self.assertIsInstance(report.get("metrics"), list)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()
