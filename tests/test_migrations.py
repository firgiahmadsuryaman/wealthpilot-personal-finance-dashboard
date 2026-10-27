"""Tes migrasi database lokal dari skema MVP sebelumnya."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from unittest.mock import patch

from app import main


class DatabaseMigrationTests(unittest.TestCase):
    def test_legacy_market_snapshot_schema_is_migrated_without_losing_rows(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "legacy.db"
            conn = sqlite3.connect(db_path)
            conn.executescript("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    tx_type TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    unit_price REAL NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'IDR',
                    fx_rate REAL NOT NULL DEFAULT 1,
                    fee_idr REAL NOT NULL DEFAULT 0,
                    amount_idr REAL NOT NULL DEFAULT 0,
                    memo TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE pegadaian_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    customer_buy_idr_g REAL NOT NULL,
                    customer_sell_idr_g REAL NOT NULL,
                    source TEXT NOT NULL DEFAULT 'Tring! by Pegadaian (input manual)',
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    percent_change REAL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL
                );
                INSERT INTO market_snapshots(symbol, price, percent_change, timestamp, source)
                VALUES('SPY', 550, 0.2, '2026-10-27T20:00:00+00:00', 'Twelve Data');
            """)
            conn.commit()
            conn.close()
            with patch.object(main, "DB_PATH", db_path):
                main.init_db()
                with main.connect() as db:
                    columns = {row[1] for row in db.execute("PRAGMA table_info(market_snapshots)").fetchall()}
                    snapshot = db.execute("SELECT * FROM market_snapshots WHERE symbol='SPY'").fetchone()
                    tx_columns = {row[1] for row in db.execute("PRAGMA table_info(transactions)").fetchall()}
                    gold_columns = {row[1] for row in db.execute("PRAGMA table_info(pegadaian_rates)").fetchall()}
            self.assertIn("timestamp_precision", columns)
            self.assertEqual(snapshot["price"], 550)
            self.assertIn("price_unit", tx_columns)
            self.assertIn("unit_price_entered", tx_columns)
            self.assertIn("quote_unit", gold_columns)
            self.assertIn("customer_buy_entered", gold_columns)


if __name__ == "__main__":
    unittest.main()
