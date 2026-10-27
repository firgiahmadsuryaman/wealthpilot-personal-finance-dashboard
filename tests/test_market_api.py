"""Tes harga Pegadaian manual dan penanganan quote provider."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient
from app import main


class MarketApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "market-test.db"
        self.db_patch = patch.object(main, "DB_PATH", self.db_path)
        self.db_patch.start()
        main._quote_cache.clear()
        main._quote_cache_time.clear()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.db_patch.stop()
        self.temp_dir.cleanup()
        main._quote_cache.clear()
        main._quote_cache_time.clear()

    def test_gold_price_001g_normalizes_to_per_gram(self):
        response = self.client.post("/api/market/pegadaian", json={
            "customer_buy_price": 20_000,
            "customer_sell_price": 19_000,
            "quote_unit": "0.01G",
            "captured_at": (main.datetime.now(main.timezone.utc) - main.timedelta(minutes=3)).isoformat(),
        })
        self.assertEqual(response.status_code, 200, response.text)
        rate = response.json()["rate"]
        self.assertEqual(rate["customer_buy_idr_g"], 2_000_000)
        self.assertEqual(rate["customer_sell_idr_g"], 1_900_000)
        self.assertEqual(rate["customer_sell_entered"], 19_000)


    def test_missing_api_key_does_not_fabricate_market_price(self):
        with patch.object(main, "API_KEY", ""):
            market = self.client.get("/api/market").json()
        self.assertEqual(market["spy"]["status"], "not_configured")
        self.assertIsNone(market["spy"]["price"])
        self.assertEqual(market["fx"]["status"], "not_configured")
        self.assertIsNone(market["fx"]["price"])

    def test_invalid_gold_timestamp_is_rejected(self):
        response = self.client.post("/api/market/pegadaian", json={
            "customer_buy_price": 20_000, "customer_sell_price": 19_000,
            "quote_unit": "0.01G", "captured_at": "waktu-ngawur",
        })
        self.assertEqual(response.status_code, 422)

    def test_future_gold_timestamp_is_rejected(self):
        future = (main.datetime.now(main.timezone.utc) + main.timedelta(hours=2)).isoformat()
        response = self.client.post("/api/market/pegadaian", json={
            "customer_buy_price": 20_000, "customer_sell_price": 19_000,
            "quote_unit": "0.01G", "captured_at": future,
        })
        self.assertEqual(response.status_code, 422)

    def test_non_finite_gold_prices_are_rejected(self):
        response = self.client.post("/api/market/pegadaian", json={
            "customer_buy_price": "Infinity", "customer_sell_price": 19_000,
            "quote_unit": "0.01G",
        })
        self.assertEqual(response.status_code, 422)

    def test_session_date_is_not_misrepresented_as_exact_quote_time(self):
        payload = {
            "symbol": "SPY", "currency": "USD", "close": "550.25",
            "previous_close": "548.00", "change": "2.25", "percent_change": "0.4106",
            "datetime": "2026-10-28", "timestamp": 1793145600,
            "is_market_open": False,
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        with patch.object(main, "API_KEY", "test-key"), patch.object(main.httpx, "get", return_value=response):
            quote = main._quote_from_twelvedata("SPY", 30)
        self.assertEqual(quote["timestamp"], "2026-10-28")
        self.assertEqual(quote["timestamp_precision"], "session_date")

    def test_quote_prefers_last_quote_timestamp_and_stores_snapshot(self):
        payload = {
            "symbol": "SPY", "currency": "USD", "close": "550.25",
            "previous_close": "548.00", "change": "2.25", "percent_change": "0.4106",
            "datetime": "2026-10-28", "timestamp": 1793145600,
            "last_quote_at": 1793145900, "is_market_open": True,
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        with patch.object(main, "API_KEY", "test-key"), patch.object(main.httpx, "get", return_value=response):
            quote = main._quote_from_twelvedata("SPY", 30)
        self.assertEqual(quote["status"], "ok")
        self.assertEqual(quote["price"], 550.25)
        self.assertNotEqual(quote["timestamp"], "2026-10-28")
        with main.connect() as db:
            row = db.execute("SELECT * FROM market_snapshots WHERE symbol='SPY'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["price"], 550.25)
        self.assertEqual(row["timestamp_precision"], "exact_quote")


    def test_market_history_accepts_usd_idr_symbol_with_slash(self):
        response = self.client.get("/api/market/history/USD/IDR?limit=10")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["items"], [])

    def test_provider_error_falls_back_to_marked_stale_snapshot(self):
        with main.connect() as db:
            db.execute(
                "INSERT INTO market_snapshots(symbol, price, percent_change, timestamp, source) VALUES(?,?,?,?,?)",
                ("SPY", 500.0, 0.5, "2026-10-27T20:00:00+00:00", "Twelve Data"),
            )
        with patch.object(main, "API_KEY", "test-key"), patch.object(main.httpx, "get", side_effect=httpx.ConnectError("offline")):
            quote = main._quote_from_twelvedata("SPY", 30)
        self.assertEqual(quote["status"], "stale")
        self.assertEqual(quote["price"], 500.0)
        self.assertIn("tersimpan", quote["message"])


if __name__ == "__main__":
    unittest.main()
