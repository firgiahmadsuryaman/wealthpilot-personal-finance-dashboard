"""API tests for custom financial goals (uses a temporary SQLite database)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main


class GoalCrudApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "goals-test.db"
        self.db_path_patch = patch.object(main, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def test_create_custom_goal(self):
        response = self.client.post(
            "/api/goals",
            json={
                "name": "Dana sertifikasi",
                "target_idr": 12_000_000,
                "current_saved_idr": 1_500_000,
                "target_date": "2028-12-31",
                "notes": "Target bebas buatan pengguna",
            },
        )
        self.assertEqual(response.status_code, 200)
        goal = response.json()["goal"]
        self.assertEqual(goal["name"], "Dana sertifikasi")
        self.assertEqual(goal["target_idr"], 12_000_000)
        self.assertEqual(goal["current_saved_idr"], 1_500_000)

    def test_update_custom_goal(self):
        created = self.client.post(
            "/api/goals",
            json={"name": "Dana pendidikan", "target_idr": 5_000_000},
        ).json()["goal"]
        response = self.client.put(
            f"/api/goals/{created['id']}",
            json={
                "name": "Dana pendidikan lanjutan",
                "target_idr": 8_000_000,
                "current_saved_idr": 750_000,
                "target_date": None,
                "notes": "Target diperbarui",
            },
        )
        self.assertEqual(response.status_code, 200)
        updated = response.json()["goal"]
        self.assertEqual(updated["name"], "Dana pendidikan lanjutan")
        self.assertEqual(updated["target_idr"], 8_000_000)
        self.assertEqual(updated["current_saved_idr"], 750_000)

    def test_blank_goal_name_is_rejected(self):
        response = self.client.post(
            "/api/goals",
            json={"name": "   ", "target_idr": 1_000_000},
        )
        self.assertEqual(response.status_code, 422)

    def test_update_missing_goal_returns_404(self):
        response = self.client.put(
            "/api/goals/9999",
            json={"name": "Target tidak ada", "target_idr": 1_000_000},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
