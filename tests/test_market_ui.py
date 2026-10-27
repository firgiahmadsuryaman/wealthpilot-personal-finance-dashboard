"""Tes statis ringan untuk memastikan Market Monitor menampilkan data dan diagnosis."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketMonitorUiTests(unittest.TestCase):
    def test_market_monitor_contains_real_series_controls_and_metrics(self):
        html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
        for token in (
            'id="spyChartRange"',
            'id="spyHistoryChart"',
            'id="spyChartStatus"',
            'id="spyRangeChange"',
            'id="spyLastClose"',
            'id="spyChartMessage"',
            'app.js?v=0.4.1',
            'style.css?v=0.4.1',
        ):
            with self.subTest(token=token):
                self.assertIn(token, html)

    def test_frontend_loads_provider_series_and_exposes_error_message(self):
        js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("/api/market/series/SPY?range=", js)
        self.assertIn("spyChartMessage", js)
        self.assertIn("Perubahan rentang:", js)
        self.assertIn("Close candle terakhir:", js)


if __name__ == "__main__":
    unittest.main()
