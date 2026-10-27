"""Tes ekspor transaksi untuk pencadangan pribadi."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import main


class ExportApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_patch = patch.object(main, "DB_PATH", Path(self.temp_dir.name) / "exports-test.db")
        self.db_patch.start()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_export_backup_contains_local_tables_but_not_provider_secret(self):
        self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 100_000,
        })
        self.client.post("/api/goals", json={"name": "Dana masa depan", "target_idr": 1_000_000})
        self.client.post("/api/market/pegadaian", json={
            "customer_buy_price": 20_000, "customer_sell_price": 19_000, "quote_unit": "0.01G",
        })
        response = self.client.get("/api/export/backup.json")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("application/json", response.headers["content-type"])
        payload = json.loads(response.content)
        self.assertEqual(payload["application"], "WealthPilot")
        self.assertEqual(payload["backup_version"], 1)
        self.assertEqual(len(payload["tables"]["transactions"]), 1)
        self.assertEqual(len(payload["tables"]["goals"]), 1)
        self.assertEqual(len(payload["tables"]["pegadaian_rates"]), 1)
        self.assertNotIn("TWELVE_DATA_API_KEY", response.text)

    def test_favicon_route_does_not_return_404(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/svg+xml", response.headers["content-type"])

    def test_export_csv_uses_utf8_bom_and_indonesian_headers(self):
        self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 750_000,
            "memo": "=HYPERLINK(\"https://example.invalid\",\"buka\")",
        })
        response = self.client.get("/api/export/transactions.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("attachment; filename=\"wealthpilot-transaksi.csv\"", response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Tanggal".encode(), response.content)
        self.assertIn("'=HYPERLINK".encode(), response.content)


if __name__ == "__main__":
    unittest.main()
