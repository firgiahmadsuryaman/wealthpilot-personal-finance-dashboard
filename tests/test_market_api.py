"""Tes quote emas spot bid/ask, endpoint legacy Pegadaian, dan market-data."""
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
        main._series_cache.clear()
        main._series_cache_time.clear()
        main._gold_raw_cache.clear()
        main._gold_raw_cache_time = 0.0
        main._gold_series_cache.clear()
        main._gold_series_cache_time.clear()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.db_patch.stop()
        self.temp_dir.cleanup()
        main._quote_cache.clear()
        main._quote_cache_time.clear()
        main._series_cache.clear()
        main._series_cache_time.clear()
        main._gold_raw_cache.clear()
        main._gold_raw_cache_time = 0.0
        main._gold_series_cache.clear()
        main._gold_series_cache_time.clear()

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
        with patch.object(main, "API_KEY", ""), patch.object(main, "_fetch_standard_bullion_quote", return_value={
            "status": "error", "source": "Standard Bullion", "timestamp": None,
            "ask_usd_oz": None, "bid_usd_oz": None, "message": "network not mocked",
            "attribution": "Data by Standard Bullion",
        }):
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
        with patch.object(main, "API_KEY", "test-key"), patch.object(main.httpx, "get", return_value=response) as get:
            quote = main._quote_from_twelvedata("SPY", 30)
        self.assertEqual(quote["status"], "ok")
        self.assertEqual(quote["price"], 550.25)
        self.assertEqual(get.call_args.kwargs["params"]["interval"], "1min")
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

    def test_series_endpoint_returns_real_provider_candles_and_persists_history(self):
        payload = {
            "meta": {"symbol": "SPY", "interval": "1min", "currency": "USD", "exchange_timezone": "America/New_York"},
            "values": [
                {"datetime": "2026-10-28 10:02:00", "open": "650.1", "high": "650.5", "low": "649.9", "close": "650.4", "volume": "1200"},
                {"datetime": "2026-10-28 10:01:00", "open": "649.8", "high": "650.2", "low": "649.7", "close": "650.1", "volume": "1400"},
            ],
            "status": "ok",
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        with patch.object(main, "API_KEY", "test-key"), patch.object(main.httpx, "get", return_value=response) as get:
            result = self.client.get("/api/market/series/SPY?range=1D&force=true").json()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["interval"], "1min")
        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["items"][0]["datetime"], "2026-10-28 10:01:00")
        self.assertEqual(result["items"][0]["price"], 650.1)
        self.assertEqual(result["items"][-1]["price"], 650.4)
        self.assertTrue(get.call_args.args[0].endswith("/time_series"))
        self.assertEqual(get.call_args.kwargs["params"]["interval"], "1min")
        with main.connect() as db:
            rows = db.execute("SELECT * FROM market_bars WHERE symbol='SPY' AND bar_interval='1min'").fetchall()
        self.assertEqual(len(rows), 2)

    def test_series_endpoint_does_not_invent_data_without_api_key(self):
        with patch.object(main, "API_KEY", ""):
            result = self.client.get("/api/market/series/SPY?range=1D").json()
        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(result["items"], [])
        self.assertIn("TWELVE_DATA_API_KEY", result["message"])

    def test_series_endpoint_uses_persisted_bars_as_explicitly_stale_fallback(self):
        with main.connect() as db:
            db.execute(
                "INSERT INTO market_bars(symbol, bar_interval, datetime, open, high, low, close, volume, source, fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("SPY", "1min", "2026-10-28 10:00:00", 649.0, 650.0, 648.0, 649.5, 100, "Twelve Data", "2026-10-28T14:00:00+00:00"),
            )
        with patch.object(main, "API_KEY", "test-key"), patch.object(main.httpx, "get", side_effect=httpx.ConnectError("offline")):
            result = self.client.get("/api/market/series/SPY?range=1D&force=true").json()
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["items"][0]["price"], 649.5)
        self.assertIn("pembaruan provider gagal", result["message"])

    def test_invalid_series_range_is_rejected(self):
        response = self.client.get("/api/market/series/SPY?range=3H")
        self.assertEqual(response.status_code, 400)

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


    def test_market_endpoint_exposes_gold_buy_sell_and_mid_price(self):
        updated = main.datetime.now(main.timezone.utc).isoformat(timespec="seconds")
        def quote(symbol, _ttl, force=False):
            if symbol == "USD/IDR":
                return {"status": "ok", "price": 16_000.0, "timestamp": updated, "source": "Twelve Data"}
            return {"status": "ok", "price": 550.0, "percent_change": 0.5, "timestamp": updated, "source": "Twelve Data"}
        raw_gold = {
            "status": "ok", "source": "Standard Bullion", "timestamp": updated,
            "ask_usd_oz": 4050.0, "bid_usd_oz": 4040.0,
            "change_today": {"percent": 1.25}, "attribution": "Data by Standard Bullion",
        }
        with patch.object(main, "_quote_from_twelvedata", side_effect=quote), \
             patch.object(main, "_fetch_standard_bullion_quote", return_value=raw_gold):
            response = self.client.get("/api/market")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        gold = payload["gold"]["data"]
        self.assertEqual(payload["gold"]["source"], "Standard Bullion")
        self.assertAlmostEqual(gold["customer_buy_idr_g"], 4050.0 * 16000.0 / main.TROY_OUNCE_GRAMS)
        self.assertAlmostEqual(gold["customer_sell_idr_g"], 4040.0 * 16000.0 / main.TROY_OUNCE_GRAMS)
        self.assertGreater(gold["customer_buy_idr_g"], gold["customer_sell_idr_g"])
        self.assertIn("refresh_seconds", payload)

    def test_standard_bullion_bid_ask_converts_usd_oz_to_idr_per_gram(self):
        updated = main.datetime.now(main.timezone.utc).isoformat(timespec="seconds")
        payload = {
            "source": "Standard Bullion", "url": "https://standardbullion.com",
            "updated": updated, "attribution": "Data by Standard Bullion — https://standardbullion.com",
            "disclaimer": "Indicative live dealer prices.",
            "metals": [{"symbol": "XAU", "name": "Gold", "ask": 4050.0, "bid": 4040.0,
                        "open": 4000.0, "changeToday": {"amount": 50.0, "percent": 1.25},
                        "changes": {"1w": 0.5}}],
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        fx = {"status": "ok", "price": 16000.0, "timestamp": updated}
        with patch.object(main.httpx, "get", return_value=response):
            quote = main.gold_spot_quote(fx, force=True)
        self.assertEqual(quote["status"], "ok")
        self.assertAlmostEqual(quote["customer_buy_idr_g"], 4050.0 * 16000.0 / main.TROY_OUNCE_GRAMS, places=6)
        self.assertAlmostEqual(quote["customer_sell_idr_g"], 4040.0 * 16000.0 / main.TROY_OUNCE_GRAMS, places=6)
        self.assertGreater(quote["customer_buy_idr_g"], quote["customer_sell_idr_g"])
        self.assertAlmostEqual(quote["spot_mid_idr_g"], (quote["customer_buy_idr_g"] + quote["customer_sell_idr_g"]) / 2)
        self.assertEqual(quote["source"], "Standard Bullion")
        self.assertIn("bukan harga resmi Pegadaian", quote["valuation_note"])
        with main.connect() as db:
            ask_row = db.execute("SELECT * FROM market_snapshots WHERE symbol='GOLD/IDR_GRAM_ASK'").fetchone()
            bid_row = db.execute("SELECT * FROM market_snapshots WHERE symbol='GOLD/IDR_GRAM_BID'").fetchone()
        self.assertIsNotNone(ask_row)
        self.assertIsNotNone(bid_row)

    def test_gold_series_endpoint_converts_real_provider_history_with_current_fx(self):
        updated = main.datetime.now(main.timezone.utc).isoformat(timespec="seconds")
        payload = {
            "source": "Standard Bullion", "attribution": "Data by Standard Bullion",
            "metal": "XAU", "unit": "USD per troy ounce", "range": "24h", "grain": "15-minute",
            "points": [
                {"t": "2026-10-28T01:00:00Z", "price": 4000.0},
                {"t": "2026-10-28T01:15:00Z", "price": 4010.0},
            ],
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        with patch.object(main, "_quote_from_twelvedata", return_value={"status": "ok", "price": 16000.0, "timestamp": updated}), \
             patch.object(main.httpx, "get", return_value=response) as get:
            result = self.client.get("/api/market/gold/series?range=1D&force=true").json()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["item_count"], 2)
        self.assertAlmostEqual(result["items"][0]["price"], 4000.0 * 16000.0 / main.TROY_OUNCE_GRAMS, places=6)
        self.assertEqual(get.call_args.kwargs["params"], {"metal": "XAU", "range": "24h"})
        self.assertIn("kurs USD/IDR terkini", result["note"])

    def test_gold_series_without_fx_does_not_invent_idr_prices(self):
        with patch.object(main, "_quote_from_twelvedata", return_value={"status": "not_configured", "price": None}):
            result = self.client.get("/api/market/gold/series?range=1D").json()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["items"], [])
        self.assertIn("Kurs USD/IDR tidak tersedia", result["message"])

    def test_gold_series_fallback_filters_points_to_selected_range(self):
        now = main.datetime.now(main.timezone.utc)
        rows = [
            ("GOLD/IDR_GRAM_BID", 2_000_000.0, None, (now - main.timedelta(days=40)).isoformat(timespec="seconds"), "Standard Bullion × USD/IDR", "provider_timestamp"),
            ("GOLD/IDR_GRAM_BID", 2_100_000.0, None, (now - main.timedelta(days=2)).isoformat(timespec="seconds"), "Standard Bullion × USD/IDR", "provider_timestamp"),
            ("GOLD/IDR_GRAM_BID", 2_200_000.0, None, (now - main.timedelta(minutes=30)).isoformat(timespec="seconds"), "Standard Bullion × USD/IDR", "provider_timestamp"),
        ]
        with main.connect() as db:
            db.executemany(
                "INSERT INTO market_snapshots(symbol, price, percent_change, timestamp, source, timestamp_precision) VALUES(?,?,?,?,?,?)",
                rows,
            )
        with patch.object(main, "_quote_from_twelvedata", return_value={"status": "not_configured", "price": None}):
            result = self.client.get("/api/market/gold/series?range=1D").json()
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["items"][0]["price"], 2_200_000.0)

    def test_gold_series_does_not_force_extra_fx_quote_on_range_change(self):
        updated = main.datetime.now(main.timezone.utc).isoformat(timespec="seconds")
        payload = {
            "attribution": "Data by Standard Bullion", "grain": "15-minute",
            "points": [
                {"t": "2026-10-28T01:00:00Z", "price": 4000.0},
                {"t": "2026-10-28T01:15:00Z", "price": 4010.0},
            ],
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        with patch.object(main, "_quote_from_twelvedata", return_value={"status": "ok", "price": 16000.0, "timestamp": updated}) as fx_call, \
             patch.object(main.httpx, "get", return_value=response):
            result = self.client.get("/api/market/gold/series?range=1D&force=true").json()
        self.assertEqual(result["status"], "ok")
        fx_call.assert_called_once_with("USD/IDR", main.USDIDR_CACHE_SECONDS, force=False)

    def test_gold_series_rejects_unsupported_range(self):
        response = self.client.get("/api/market/gold/series?range=3H")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
