"""Tes API ledger untuk transaksi yang masuk akal dan rollback yang aman."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import main


class TransactionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "transactions-test.db"
        self.db_patch = patch.object(main, "DB_PATH", self.db_path)
        self.db_patch.start()
        self.key_patch = patch.object(main, "API_KEY", "")
        self.key_patch.start()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.db_patch.stop()
        self.key_patch.stop()
        self.temp_dir.cleanup()

    def test_deposit_and_gold_purchase_keep_contribution_separate(self):
        deposit = self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 5_000_000,
        })
        self.assertEqual(deposit.status_code, 200, deposit.text)
        buy = self.client.post("/api/transactions", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_500_000, "currency": "IDR", "price_unit": "GRAM",
        })
        self.assertEqual(buy.status_code, 200, buy.text)
        overview = self.client.get("/api/overview").json()["portfolio"]
        self.assertEqual(overview["net_contributions_idr"], 5_000_000)
        self.assertEqual(overview["cash_balance_idr"], 3_500_000)
        self.assertFalse(overview["valuation_complete"])
        self.assertIsNone(overview["portfolio_value_idr"])

    def test_buy_without_recorded_cash_is_rejected(self):
        response = self.client.post("/api/transactions", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_500_000, "currency": "IDR", "price_unit": "GRAM",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Saldo kas portofolio tidak cukup", response.json()["detail"])
        self.assertEqual(self.client.get("/api/transactions").json()["items"], [])

    def test_sell_more_than_holdings_is_rejected_atomically(self):
        self.client.post("/api/transactions", json={
            "tx_type": "OPENING", "asset": "GOLD", "quantity": 0.5,
            "unit_price": 1_500_000, "currency": "IDR", "price_unit": "GRAM",
        })
        response = self.client.post("/api/transactions", json={
            "tx_type": "SELL", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_600_000, "currency": "IDR", "price_unit": "GRAM",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("melebihi unit", response.json()["detail"])
        self.assertEqual(len(self.client.get("/api/transactions").json()["items"]), 1)

    def test_non_finite_transaction_values_are_rejected(self):
        response = self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": "Infinity",
        })
        self.assertEqual(response.status_code, 422)

    def test_fee_cannot_exceed_transaction_gross(self):
        response = self.client.post("/api/transactions", json={
            "tx_type": "OPENING", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_000_000, "currency": "IDR", "price_unit": "GRAM",
            "fee_idr": 1_000_001,
        })
        self.assertEqual(response.status_code, 422)

    def test_gold_price_per_001g_is_normalized_to_per_gram(self):
        response = self.client.post("/api/transactions", json={
            "tx_type": "OPENING", "asset": "GOLD", "quantity": 0.5,
            "unit_price": 19_000, "currency": "IDR", "price_unit": "0.01G",
        })
        self.assertEqual(response.status_code, 200, response.text)
        row = self.client.get("/api/transactions").json()["items"][0]
        self.assertAlmostEqual(row["unit_price"], 1_900_000)
        self.assertEqual(row["unit_price_entered"], 19_000)
        self.assertEqual(row["price_unit"], "0.01G")



    def test_update_transaction_succeeds_when_ledger_stays_valid(self):
        deposit = self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 5_000_000,
        }).json()
        buy = self.client.post("/api/transactions", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_500_000, "currency": "IDR", "price_unit": "GRAM",
        }).json()
        response = self.client.put(f"/api/transactions/{buy['id']}", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_600_000, "currency": "IDR", "price_unit": "GRAM",
            "memo": "Harga diperbaiki berdasarkan riwayat transaksi",
        })
        self.assertEqual(response.status_code, 200, response.text)
        rows = self.client.get("/api/transactions").json()["items"]
        edited = next(row for row in rows if row["id"] == buy["id"])
        self.assertEqual(edited["unit_price"], 1_600_000)
        self.assertEqual(edited["memo"], "Harga diperbaiki berdasarkan riwayat transaksi")
        self.assertEqual(len(rows), 2)

    def test_invalid_transaction_edit_is_rolled_back(self):
        self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 2_000_000,
        })
        buy = self.client.post("/api/transactions", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_000_000, "currency": "IDR", "price_unit": "GRAM",
        }).json()
        response = self.client.put(f"/api/transactions/{buy['id']}", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 5,
            "unit_price": 1_000_000, "currency": "IDR", "price_unit": "GRAM",
        })
        self.assertEqual(response.status_code, 400)
        row = next(row for row in self.client.get("/api/transactions").json()["items"] if row["id"] == buy["id"])
        self.assertEqual(row["quantity"], 1)

    def test_deleting_required_deposit_is_rejected_and_rolled_back(self):
        deposit = self.client.post("/api/transactions", json={
            "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 5_000_000,
        }).json()
        self.client.post("/api/transactions", json={
            "tx_type": "BUY", "asset": "GOLD", "quantity": 1,
            "unit_price": 1_500_000, "currency": "IDR", "price_unit": "GRAM",
        })
        response = self.client.delete(f"/api/transactions/{deposit['id']}")
        self.assertEqual(response.status_code, 400)
        rows = self.client.get("/api/transactions").json()["items"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(any(row["tx_type"] == "DEPOSIT" for row in rows))


    def test_timezone_naive_transaction_time_is_normalized_to_utc(self):
        response = self.client.post("/api/transactions", json={
            "occurred_at": "2026-10-28T09:30:00", "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 100_000,
        })
        self.assertEqual(response.status_code, 200, response.text)
        row = self.client.get("/api/transactions").json()["items"][0]
        self.assertEqual(row["occurred_at"], "2026-10-28T09:30:00+00:00")

    def test_invalid_transaction_datetime_is_rejected(self):
        response = self.client.post("/api/transactions", json={
            "occurred_at": "bukan-tanggal", "tx_type": "DEPOSIT", "asset": "CASH", "amount_idr": 100_000,
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
