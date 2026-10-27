from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "wealthpilot.db"
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
SPY_CACHE_SECONDS = max(30, int(os.getenv("SPY_CACHE_SECONDS", "60")))
USDIDR_CACHE_SECONDS = max(60, int(os.getenv("USDIDR_CACHE_SECONDS", "900")))
SPY_QUOTE_INTERVAL = os.getenv("SPY_QUOTE_INTERVAL", "1min").strip() or "1min"
USDIDR_QUOTE_INTERVAL = os.getenv("USDIDR_QUOTE_INTERVAL", "1min").strip() or "1min"
SPY_SERIES_CACHE_SECONDS = max(60, int(os.getenv("SPY_SERIES_CACHE_SECONDS", "60")))

app = FastAPI(title="WealthPilot", version="0.4.1", description="Personal investment dashboard; local-first MVP")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

_quote_cache: dict[str, dict] = {}
_quote_cache_time: dict[str, float] = {}
_series_cache: dict[str, dict] = {}
_series_cache_time: dict[str, float] = {}

# Rentang grafik: intraday memakai candle 1 menit atau 5 menit; rentang panjang memakai candle harian.
SERIES_RANGES = {
    "1D": ("1min", 390),
    "5D": ("5min", 390),
    "1M": ("1day", 30),
    "1Y": ("1day", 252),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection and always commit/rollback/close it."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                created_at TEXT NOT NULL,
                price_unit TEXT NOT NULL DEFAULT 'UNIT',
                unit_price_entered REAL
            );
            CREATE TABLE IF NOT EXISTS pegadaian_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                customer_buy_idr_g REAL NOT NULL,
                customer_sell_idr_g REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'Tring! by Pegadaian (input manual)',
                notes TEXT NOT NULL DEFAULT '',
                quote_unit TEXT NOT NULL DEFAULT 'GRAM',
                customer_buy_entered REAL,
                customer_sell_entered REAL
            );
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_idr REAL NOT NULL,
                current_saved_idr REAL NOT NULL DEFAULT 0,
                target_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                percent_change REAL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp_precision TEXT NOT NULL DEFAULT 'provider_timestamp'
            );
            CREATE TABLE IF NOT EXISTS market_bars (
                symbol TEXT NOT NULL,
                bar_interval TEXT NOT NULL,
                datetime TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume REAL,
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY(symbol, bar_interval, datetime)
            );
            """
        )
        # Safe small migrations for a database created by an earlier MVP build.
        tx_columns = {row[1] for row in db.execute("PRAGMA table_info(transactions)").fetchall()}
        if "price_unit" not in tx_columns:
            db.execute("ALTER TABLE transactions ADD COLUMN price_unit TEXT NOT NULL DEFAULT 'UNIT'")
        if "unit_price_entered" not in tx_columns:
            db.execute("ALTER TABLE transactions ADD COLUMN unit_price_entered REAL")
        market_columns = {row[1] for row in db.execute("PRAGMA table_info(market_snapshots)").fetchall()}
        if "timestamp_precision" not in market_columns:
            db.execute("ALTER TABLE market_snapshots ADD COLUMN timestamp_precision TEXT NOT NULL DEFAULT 'provider_timestamp'")
        columns = {row[1] for row in db.execute("PRAGMA table_info(pegadaian_rates)").fetchall()}
        if "quote_unit" not in columns:
            db.execute("ALTER TABLE pegadaian_rates ADD COLUMN quote_unit TEXT NOT NULL DEFAULT 'GRAM'")
        if "customer_buy_entered" not in columns:
            db.execute("ALTER TABLE pegadaian_rates ADD COLUMN customer_buy_entered REAL")
        if "customer_sell_entered" not in columns:
            db.execute("ALTER TABLE pegadaian_rates ADD COLUMN customer_sell_entered REAL")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "app" / "static" / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Hindari permintaan ikon yang berakhir 404 pada browser tertentu.
    return FileResponse(BASE_DIR / "app" / "static" / "favicon.svg", media_type="image/svg+xml")


# ---------- Market data ----------

def _quote_from_twelvedata(symbol: str, ttl: int, force: bool = False) -> dict:
    """Ambil quote provider dan pertahankan sumber serta waktu quote aslinya."""
    if not API_KEY:
        return {
            "status": "not_configured",
            "symbol": symbol,
            "message": "TWELVE_DATA_API_KEY belum diisi di file .env.",
            "source": "Twelve Data",
            "price": None,
            "timestamp": None,
            "timestamp_precision": "unavailable",
            "interval": SPY_QUOTE_INTERVAL if symbol == "SPY" else USDIDR_QUOTE_INTERVAL,
        }

    now = time.time()
    if not force and symbol in _quote_cache and now - _quote_cache_time.get(symbol, 0) < ttl:
        return dict(_quote_cache[symbol], cache_status="cached")

    interval = SPY_QUOTE_INTERVAL if symbol == "SPY" else USDIDR_QUOTE_INTERVAL
    try:
        response = httpx.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": symbol, "interval": interval, "apikey": API_KEY},
            timeout=12.0,
            headers={"User-Agent": "WealthPilot/0.3 personal-dashboard"},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Format respons provider tidak dikenali.")
        if data.get("status") == "error" or data.get("code"):
            message = data.get("message") or data.get("description") or "Penyedia data mengembalikan error."
            return _stale_quote_or_error(symbol, message)

        # Jangan menampilkan waktu server sebagai waktu quote. Beberapa respons
        # menyertakan waktu quote yang jelas, sementara yang lain hanya tanggal
        # sesi atau timestamp candle. Simpan tingkat presisinya secara eksplisit.
        quote_timestamp = None
        timestamp_precision = "unavailable"
        raw_last_quote_at = data.get("last_quote_at")
        if raw_last_quote_at not in (None, ""):
            try:
                quote_timestamp = datetime.fromtimestamp(float(raw_last_quote_at), timezone.utc).isoformat(timespec="seconds")
                timestamp_precision = "exact_quote"
            except (TypeError, ValueError, OSError, OverflowError):
                quote_timestamp = None
        if quote_timestamp is None:
            raw_datetime = data.get("datetime")
            if raw_datetime not in (None, ""):
                quote_timestamp = str(raw_datetime)
                timestamp_precision = "session_date" if len(quote_timestamp) <= 10 and ":" not in quote_timestamp else "provider_datetime"
            elif data.get("timestamp") not in (None, ""):
                try:
                    quote_timestamp = datetime.fromtimestamp(float(data["timestamp"]), timezone.utc).isoformat(timespec="seconds")
                    timestamp_precision = "provider_timestamp"
                except (TypeError, ValueError, OSError, OverflowError):
                    quote_timestamp = None
                    timestamp_precision = "unavailable"

        price_value = data.get("close")
        if price_value in (None, ""):
            price_value = data.get("price") if data.get("price") not in (None, "") else data.get("last")
        price = _to_float(price_value)
        if price is None or price <= 0:
            return _stale_quote_or_error(symbol, "Provider tidak mengirim harga positif yang valid.")

        result = {
            "status": "ok",
            "symbol": symbol,
            "price": price,
            "currency": data.get("currency") or ("USD" if symbol == "SPY" else "IDR"),
            "change": _to_float(data.get("change")),
            "percent_change": _to_float(data.get("percent_change")),
            "previous_close": _to_float(data.get("previous_close")),
            "timestamp": quote_timestamp,
            "timestamp_precision": timestamp_precision,
            "market_open": data.get("is_market_open"),
            "interval": interval,
            "source": "Twelve Data",
            "cache_status": "fresh",
            "message": None,
        }
        _quote_cache[symbol] = result
        _quote_cache_time[symbol] = now

        try:
            with connect() as db:
                last = db.execute(
                    "SELECT timestamp, price FROM market_snapshots WHERE symbol=? ORDER BY id DESC LIMIT 1",
                    (symbol,),
                ).fetchone()
                # Simpan snapshot baru jika waktu quote berubah atau harga berubah.
                if not last or last["timestamp"] != quote_timestamp or float(last["price"]) != price:
                    db.execute(
                        "INSERT INTO market_snapshots(symbol, price, percent_change, timestamp, source, timestamp_precision) VALUES(?,?,?,?,?,?)",
                        (symbol, price, result["percent_change"], quote_timestamp or "", "Twelve Data", timestamp_precision),
                    )
        except sqlite3.Error:
            # Quote masih bisa dipakai untuk sesi ini; kegagalan histori tidak boleh
            # mengubah harga provider menjadi nol atau memutus respons dashboard.
            pass
        return result
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return _stale_quote_or_error(symbol, f"Gagal memperbarui quote: {exc}")


def _stale_quote_or_error(symbol: str, message: str) -> dict:
    """Gunakan quote lama dengan status stale bila provider tidak bisa dihubungi."""
    if symbol in _quote_cache:
        return dict(_quote_cache[symbol], status="stale", cache_status="stale", message=message)
    try:
        with connect() as db:
            row = db.execute(
                "SELECT * FROM market_snapshots WHERE symbol=? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row:
            previous = dict(row)
            return {
                "status": "stale",
                "cache_status": "database_fallback",
                "symbol": symbol,
                "price": float(previous["price"]),
                "percent_change": previous["percent_change"],
                "change": None,
                "previous_close": None,
                "timestamp": previous["timestamp"],
                "timestamp_precision": previous.get("timestamp_precision", "provider_timestamp"),
                "source": previous["source"],
                "currency": "USD" if symbol == "SPY" else "IDR",
                "market_open": None,
                "interval": SPY_QUOTE_INTERVAL if symbol == "SPY" else USDIDR_QUOTE_INTERVAL,
                "message": f"Menampilkan quote tersimpan; data terbaru gagal diambil. {message}",
            }
    except sqlite3.Error:
        pass
    return {
        "status": "error",
        "cache_status": "empty",
        "symbol": symbol,
        "price": None,
        "timestamp": None,
        "timestamp_precision": "unavailable",
        "source": "Twelve Data",
        "interval": SPY_QUOTE_INTERVAL if symbol == "SPY" else USDIDR_QUOTE_INTERVAL,
        "message": message,
    }


def _series_items_from_db(symbol: str, interval: str, limit: int) -> list[dict]:
    """Baca candle provider yang pernah tersimpan, tanpa membuat titik data sintetis."""
    try:
        with connect() as db:
            rows = db.execute(
                "SELECT * FROM market_bars WHERE symbol=? AND bar_interval=? ORDER BY datetime DESC LIMIT ?",
                (symbol, interval, limit),
            ).fetchall()
        items = [dict(row) for row in reversed(rows)]
        for item in items:
            item["price"] = item.get("close")
        return items
    except sqlite3.Error:
        return []


def _series_response_from_db(symbol: str, range_key: str, interval: str, limit: int, message: str) -> dict:
    items = _series_items_from_db(symbol, interval, limit)
    if items:
        return {
            "status": "stale", "cache_status": "database_fallback", "symbol": symbol,
            "range": range_key, "interval": interval, "source": "Twelve Data (snapshot tersimpan)",
            "fetched_at": items[-1].get("fetched_at"), "latest_at": items[-1].get("datetime"),
            "item_count": len(items), "items": items,
            "message": f"Menampilkan histori tersimpan; pembaruan provider gagal. {message}",
        }
    status = "not_configured" if not API_KEY else "error"
    return {
        "status": status, "cache_status": "empty", "symbol": symbol, "range": range_key,
        "interval": interval, "source": "Twelve Data", "fetched_at": None,
        "latest_at": None, "item_count": 0, "items": [], "message": message,
    }


def _series_from_twelvedata(symbol: str, range_key: str = "1D", force: bool = False) -> dict:
    """Ambil candle historis asli dari endpoint /time_series Twelve Data."""
    symbol = symbol.upper()
    if symbol != "SPY":
        raise ValueError("Grafik seri provider saat ini hanya mendukung SPY.")
    range_key = range_key.upper()
    if range_key not in SERIES_RANGES:
        raise ValueError("Rentang grafik tidak didukung. Gunakan 1D, 5D, 1M, atau 1Y.")
    interval, outputsize = SERIES_RANGES[range_key]
    cache_key = f"{symbol}:{range_key}"
    now = time.time()

    if not API_KEY:
        return _series_response_from_db(
            symbol, range_key, interval, outputsize,
            "TWELVE_DATA_API_KEY belum diisi di file .env. Masukkan API key, lalu restart server.",
        )

    if not force and cache_key in _series_cache and now - _series_cache_time.get(cache_key, 0) < SPY_SERIES_CACHE_SECONDS:
        return {**_series_cache[cache_key], "cache_status": "cached"}

    try:
        response = httpx.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "order": "asc",
                "apikey": API_KEY,
            },
            timeout=15.0,
            headers={"User-Agent": "WealthPilot/0.4.1 personal-dashboard"},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Format histori harga dari provider tidak dikenali.")
        if data.get("status") == "error" or data.get("code"):
            message = data.get("message") or data.get("description") or "Provider menolak permintaan histori harga."
            return _series_response_from_db(symbol, range_key, interval, outputsize, message)
        values = data.get("values")
        if not isinstance(values, list) or not values:
            return _series_response_from_db(
                symbol, range_key, interval, outputsize,
                "Provider tidak mengembalikan candle untuk rentang ini. Periksa paket, kuota, dan izin data.",
            )

        items = []
        fetched_at = now_iso()
        for point in values:
            if not isinstance(point, dict) or not point.get("datetime"):
                continue
            close = _to_float(point.get("close"))
            if close is None or close <= 0:
                continue
            items.append({
                "symbol": symbol,
                "bar_interval": interval,
                "datetime": str(point["datetime"]),
                "open": _to_float(point.get("open")),
                "high": _to_float(point.get("high")),
                "low": _to_float(point.get("low")),
                "close": close,
                "price": close,
                "volume": _to_float(point.get("volume")),
                "source": "Twelve Data",
                "fetched_at": fetched_at,
            })
        # Pastikan garis dibaca dari waktu paling lama ke waktu paling baru
        # karena urutan respons provider bisa berbeda menurut endpoint/plan.
        items.sort(key=lambda item: item["datetime"])
        if not items:
            return _series_response_from_db(symbol, range_key, interval, outputsize, "Tidak ada candle valid dari provider.")

        with connect() as db:
            db.executemany(
                """INSERT INTO market_bars(symbol, bar_interval, datetime, open, high, low, close, volume, source, fetched_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(symbol, bar_interval, datetime) DO UPDATE SET
                       open=excluded.open, high=excluded.high, low=excluded.low,
                       close=excluded.close, volume=excluded.volume,
                       source=excluded.source, fetched_at=excluded.fetched_at""",
                [
                    (symbol, interval, item["datetime"], item["open"], item["high"], item["low"],
                     item["close"], item["volume"], item["source"], fetched_at)
                    for item in items
                ],
            )
            # Jaga database tetap ringan; pertahankan candle terbaru per interval.
            db.execute(
                "DELETE FROM market_bars WHERE symbol=? AND bar_interval=? AND datetime NOT IN "
                "(SELECT datetime FROM market_bars WHERE symbol=? AND bar_interval=? ORDER BY datetime DESC LIMIT 2000)",
                (symbol, interval, symbol, interval),
            )

        result = {
            "status": "ok", "cache_status": "fresh", "symbol": symbol,
            "range": range_key, "interval": interval,
            "source": "Twelve Data · time_series", "fetched_at": fetched_at,
            "latest_at": items[-1]["datetime"], "item_count": len(items),
            "meta": data.get("meta") or {}, "items": items, "message": None,
            "note": "Timestamp adalah waktu pembukaan candle menurut zona waktu bursa dari provider; data live atau tertunda mengikuti paket dan lisensi API.",
        }
        _series_cache[cache_key] = result
        _series_cache_time[cache_key] = now
        return result
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return _series_response_from_db(symbol, range_key, interval, outputsize, f"Gagal mengambil histori: {exc}")


def _to_float(value):
    try:
        return float(value) if value not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def latest_gold_rates() -> Optional[dict]:
    with connect() as db:
        row = db.execute("SELECT * FROM pegadaian_rates ORDER BY captured_at DESC, id DESC LIMIT 1").fetchone()
        prev = db.execute("SELECT * FROM pegadaian_rates ORDER BY captured_at DESC, id DESC LIMIT 1 OFFSET 1").fetchone()
    if not row:
        return None
    latest = dict(row)
    latest["freshness_status"] = "ok"
    try:
        captured = datetime.fromisoformat(str(latest["captured_at"]).replace("Z", "+00:00"))
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours > 24:
            latest["freshness_status"] = "stale"
    except (TypeError, ValueError, OverflowError):
        latest["freshness_status"] = "unknown"
    latest["sellback_change_pct"] = None
    if prev and prev["customer_sell_idr_g"]:
        latest["sellback_change_pct"] = (row["customer_sell_idr_g"] / prev["customer_sell_idr_g"] - 1) * 100
    latest["source_url"] = "https://pegadaian.co.id/harga-emas"
    return latest


@app.get("/api/market")
def get_market(force: bool = False):
    gold = latest_gold_rates()
    spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS, force=force)
    fx = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS, force=force)
    if fx.get("status") in ("ok", "stale") and fx.get("price"):
        fx_rate = fx["price"]
    else:
        fx_rate = None
    return {
        "gold": {
            "status": gold.get("freshness_status", "ok") if gold else "not_configured",
            "data": gold,
            "message": None if gold else "Masukkan harga beli dan harga jual kembali yang terlihat di aplikasi Tring! by Pegadaian.",
            "source": gold["source"] if gold else "Tring! by Pegadaian",
            "real_time_note": "Pegadaian memperbarui harga secara berkala; bukan tick-by-tick.",
        },
        "spy": spy,
        "fx": fx,
        "fx_rate": fx_rate,
        "checked_at": now_iso(),
        "refresh_seconds": {"spy": SPY_CACHE_SECONDS, "fx": USDIDR_CACHE_SECONDS},
    }


class PegadaianRateInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    customer_buy_price: float = Field(gt=0, description="Harga beli persis seperti yang terlihat di Tring!")
    customer_sell_price: float = Field(gt=0, description="Harga jual kembali persis seperti yang terlihat di Tring!")
    quote_unit: Literal["GRAM", "0.01G"] = "0.01G"
    captured_at: Optional[str] = None
    source: str = Field(default="Tring! by Pegadaian (input manual)", max_length=120)
    notes: str = Field(default="", max_length=500)

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at(cls, value):
        if value is None or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Waktu harga harus berupa tanggal/waktu ISO yang valid.") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        normalized = parsed.astimezone(timezone.utc)
        if normalized > datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=5):
            raise ValueError("Waktu snapshot tidak boleh lebih dari 5 menit di masa depan.")
        return normalized.isoformat(timespec="seconds")

    @model_validator(mode="after")
    def check_prices(self):
        # Normally the price paid by a buyer should not be below the buyback paid by Pegadaian.
        # Avoid rejecting it automatically; a product or exceptional quote can differ. UI shows both.
        return self


@app.post("/api/market/pegadaian")
def save_pegadaian_rate(data: PegadaianRateInput):
    captured_at = data.captured_at or now_iso()
    # Pegadaian pricing may be quoted per gram or per 0.01 gram. Store normalized IDR/gram
    # for portfolio valuation, while retaining the raw values and unit exactly as entered.
    factor = 100.0 if data.quote_unit == "0.01G" else 1.0
    normalized_buy = data.customer_buy_price * factor
    normalized_sell = data.customer_sell_price * factor
    with connect() as db:
        cur = db.execute(
            "INSERT INTO pegadaian_rates(captured_at, customer_buy_idr_g, customer_sell_idr_g, source, notes, quote_unit, customer_buy_entered, customer_sell_entered) VALUES(?,?,?,?,?,?,?,?)",
            (captured_at, normalized_buy, normalized_sell, data.source[:120], data.notes[:500], data.quote_unit, data.customer_buy_price, data.customer_sell_price),
        )
        row_id = cur.lastrowid
    return {"ok": True, "id": row_id, "rate": latest_gold_rates()}


@app.get("/api/market/pegadaian/history")
def gold_history(limit: int = 60):
    limit = min(max(limit, 1), 365)
    with connect() as db:
        rows = db.execute("SELECT * FROM pegadaian_rates ORDER BY captured_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
    return {"items": [dict(r) for r in reversed(rows)]}


@app.get("/api/market/series/{symbol}")
def market_series(symbol: str, range: str = "1D", force: bool = False):
    """Grafik candle historis dari sumber provider, bukan hanya snapshot lokal quote."""
    symbol = symbol.upper()
    range_key = range.upper()
    if symbol != "SPY":
        raise HTTPException(status_code=400, detail="Seri provider saat ini hanya tersedia untuk SPY.")
    if range_key not in SERIES_RANGES:
        raise HTTPException(status_code=400, detail="Rentang grafik harus 1D, 5D, 1M, atau 1Y.")
    return _series_from_twelvedata(symbol, range_key, force=force)


@app.get("/api/market/history/{symbol:path}")
def market_history(symbol: str, limit: int = 120):
    symbol = symbol.upper().replace("%2F", "/")
    if symbol not in ("SPY", "USD/IDR"):
        raise HTTPException(status_code=400, detail="Symbol belum didukung.")
    limit = min(max(limit, 1), 500)
    with connect() as db:
        rows = db.execute("SELECT * FROM market_snapshots WHERE symbol=? ORDER BY id DESC LIMIT ?", (symbol, limit)).fetchall()
    return {"items": [dict(r) for r in reversed(rows)]}


# ---------- Transactions and portfolio accounting ----------
TxType = Literal["DEPOSIT", "WITHDRAW", "BUY", "SELL", "OPENING", "DIVIDEND"]
AssetType = Literal["GOLD", "SPY", "CASH"]


class TransactionInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    occurred_at: Optional[str] = None
    tx_type: TxType
    asset: AssetType
    quantity: float = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)
    currency: Literal["IDR", "USD"] = "IDR"
    price_unit: Optional[Literal["GRAM", "0.01G", "UNIT"]] = None
    fx_rate: float = Field(default=0, ge=0, description="IDR per USD; required for SPY transactions")
    fee_idr: float = Field(default=0, ge=0)
    amount_idr: float = Field(default=0, ge=0)
    memo: str = Field(default="", max_length=500)

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value):
        if value is None or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Tanggal transaksi harus berupa tanggal/waktu ISO yang valid.") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")

    @model_validator(mode="after")
    def validate_fields(self):
        if self.tx_type in ("DEPOSIT", "WITHDRAW", "DIVIDEND"):
            if self.amount_idr <= 0:
                raise ValueError("Jumlah IDR harus lebih dari 0 untuk setoran, penarikan, atau dividen.")
        elif self.tx_type in ("BUY", "SELL", "OPENING"):
            if self.asset not in ("GOLD", "SPY"):
                raise ValueError("Pilih aset Emas atau SPY untuk transaksi aset.")
            if self.quantity <= 0 or self.unit_price <= 0:
                raise ValueError("Kuantitas dan harga per unit harus lebih dari 0.")
            if self.asset == "GOLD" and self.currency != "IDR":
                raise ValueError("Harga Tabungan Emas Pegadaian harus dalam IDR per gram.")
            if self.asset == "SPY" and self.currency != "USD":
                raise ValueError("Harga SPY harus dalam USD per unit.")
            if self.asset == "GOLD" and self.price_unit == "UNIT":
                raise ValueError("Untuk emas, pilih harga per gram atau per 0,01 gram.")
            if self.asset == "SPY" and self.price_unit not in (None, "UNIT"):
                raise ValueError("Harga SPY menggunakan USD per unit.")
            if self.asset == "SPY" and self.fx_rate < 1000:
                raise ValueError("Masukkan kurs IDR per USD yang benar (contoh sekitar ribuan rupiah), jangan biarkan kosong.")
        if self.tx_type in ("DEPOSIT", "WITHDRAW", "DIVIDEND") and self.asset != "CASH":
            raise ValueError("Jenis transaksi kas harus memakai aset CASH.")
        if self.tx_type in ("DEPOSIT", "WITHDRAW") and self.fee_idr > 0:
            raise ValueError("Biaya transfer untuk setoran/penarikan belum didukung terpisah. Masukkan nilai bersih yang benar dan catat biaya pada memo.")
        if self.tx_type == "DIVIDEND" and self.fee_idr > self.amount_idr:
            raise ValueError("Biaya tidak boleh melebihi nilai dividen.")
        if self.tx_type in ("BUY", "SELL", "OPENING"):
            factor = 100.0 if self.asset == "GOLD" and self.price_unit == "0.01G" else 1.0
            gross_idr = self.quantity * self.unit_price * factor * (self.fx_rate if self.currency == "USD" else 1.0)
            if self.fee_idr > gross_idr:
                raise ValueError("Biaya transaksi tidak boleh melebihi nilai bruto transaksi.")
        return self


def _read_transactions(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT * FROM transactions ORDER BY occurred_at ASC, id ASC").fetchall()
    return [dict(r) for r in rows]


def _tx_gross_idr(tx: dict) -> float:
    if tx["tx_type"] in ("DEPOSIT", "WITHDRAW", "DIVIDEND"):
        return float(tx["amount_idr"])
    rate = float(tx["fx_rate"] or 1) if tx["currency"] == "USD" else 1.0
    return float(tx["quantity"]) * float(tx["unit_price"]) * rate


def _calculate_portfolio(txs: list[dict], gold: Optional[dict], spy: dict, fx_rate: Optional[float], fx_status: Optional[str] = None) -> dict:
    holdings = {
        "GOLD": {"quantity": 0.0, "cost_basis_idr": 0.0, "realized_pnl_idr": 0.0},
        "SPY": {"quantity": 0.0, "cost_basis_idr": 0.0, "realized_pnl_idr": 0.0},
    }
    cash = 0.0
    contributions = 0.0
    realized_total = 0.0
    for tx in txs:
        typ, asset = tx["tx_type"], tx["asset"]
        gross = _tx_gross_idr(tx)
        fee = float(tx.get("fee_idr", 0) or 0)
        pnl = 0.0
        if typ == "DEPOSIT":
            cash += gross
            contributions += gross
        elif typ == "WITHDRAW":
            cash -= gross
            contributions -= gross
        elif typ == "DIVIDEND":
            cash += gross - fee
            realized_total += gross - fee
        elif typ == "OPENING":
            h = holdings[asset]
            cost = gross + fee
            h["quantity"] += float(tx["quantity"])
            h["cost_basis_idr"] += cost
            contributions += cost
        elif typ == "BUY":
            h = holdings[asset]
            cost = gross + fee
            h["quantity"] += float(tx["quantity"])
            h["cost_basis_idr"] += cost
            cash -= cost
        elif typ == "SELL":
            h = holdings[asset]
            qty = float(tx["quantity"])
            available = h["quantity"]
            if available > 0 and qty <= available + 1e-9:
                avg_cost = h["cost_basis_idr"] / available if available else 0
                basis_sold = avg_cost * qty
                net_proceeds = gross - fee
                pnl = net_proceeds - basis_sold
                h["quantity"] = max(0.0, available - qty)
                h["cost_basis_idr"] = max(0.0, h["cost_basis_idr"] - basis_sold)
                h["realized_pnl_idr"] += pnl
                cash += net_proceeds
                realized_total += pnl
            else:
                # Legacy/deleted transaction sequences may leave a sell without enough preceding units.
                # Do not quietly falsify remaining quantities; flag it in data quality warnings below.
                pass
    gold_current_price = float(gold["customer_sell_idr_g"]) if gold else None
    spy_price = spy.get("price") if spy.get("status") in ("ok", "stale") else None
    gold_value = holdings["GOLD"]["quantity"] * gold_current_price if gold_current_price is not None else None
    fx = float(fx_rate) if fx_rate else None
    spy_value = holdings["SPY"]["quantity"] * float(spy_price) * fx if spy_price is not None and fx is not None else None
    unrealized = 0.0
    missing_valuations = []
    market_data_warnings = []
    if holdings["SPY"]["quantity"] > 0 and spy.get("status") == "stale":
        market_data_warnings.append("Harga SPY memakai snapshot lama karena provider gagal diperbarui")
    if holdings["SPY"]["quantity"] > 0 and fx_status == "stale":
        market_data_warnings.append("Kurs USD/IDR memakai snapshot lama karena provider gagal diperbarui")
    if holdings["GOLD"]["quantity"] > 0 and gold and gold.get("captured_at"):
        try:
            gold_captured = datetime.fromisoformat(str(gold["captured_at"]).replace("Z", "+00:00"))
            if gold_captured.tzinfo is None:
                gold_captured = gold_captured.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - gold_captured.astimezone(timezone.utc)).total_seconds() / 3600
            if age_hours > 24:
                market_data_warnings.append("Harga emas Pegadaian belum diperbarui lebih dari 24 jam")
        except (TypeError, ValueError, OverflowError):
            market_data_warnings.append("Waktu snapshot harga emas tidak dapat diverifikasi")
    if holdings["GOLD"]["quantity"] > 0:
        if gold_value is None:
            missing_valuations.append("Harga jual kembali Pegadaian belum dicatat")
        else:
            unrealized += gold_value - holdings["GOLD"]["cost_basis_idr"]
    if holdings["SPY"]["quantity"] > 0:
        if spy_value is None:
            missing_valuations.append("Quote SPY dan/atau USD/IDR belum tersedia")
        else:
            unrealized += spy_value - holdings["SPY"]["cost_basis_idr"]
    # Do not mislead by treating missing market data as zero. Provide a partial value and mark it incomplete.
    valued_holdings = (gold_value or 0) + (spy_value or 0)
    portfolio_value = cash + valued_holdings
    valuation_complete = not missing_valuations
    total_pnl = portfolio_value - contributions if valuation_complete else None
    total_cost_basis = sum(h["cost_basis_idr"] for h in holdings.values())
    holdings_detail = {
        "GOLD": {
            **holdings["GOLD"], "current_price": gold_current_price, "current_value_idr": gold_value,
            "unrealized_pnl_idr": (gold_value - holdings["GOLD"]["cost_basis_idr"]) if gold_value is not None else None,
            "valuation_status": "ok" if gold_value is not None or holdings["GOLD"]["quantity"] == 0 else "missing_price",
        },
        "SPY": {
            **holdings["SPY"], "current_price_usd": spy_price, "fx_rate": fx,
            "current_value_idr": spy_value,
            "unrealized_pnl_idr": (spy_value - holdings["SPY"]["cost_basis_idr"]) if spy_value is not None else None,
            "valuation_status": "ok" if spy_value is not None or holdings["SPY"]["quantity"] == 0 else "missing_price",
        },
    }
    for h in holdings_detail.values():
        h["quantity"] = round(h["quantity"], 8)
        h["cost_basis_idr"] = round(h["cost_basis_idr"], 2)
        if h.get("current_value_idr") is not None:
            h["current_value_idr"] = round(h["current_value_idr"], 2)
        if h.get("unrealized_pnl_idr") is not None:
            h["unrealized_pnl_idr"] = round(h["unrealized_pnl_idr"], 2)
    return {
        "net_contributions_idr": round(contributions, 2),
        "cash_balance_idr": round(cash, 2),
        "portfolio_value_idr": round(portfolio_value, 2) if valuation_complete else None,
        "partial_portfolio_value_idr": round(portfolio_value, 2),
        "total_pnl_idr": round(total_pnl, 2) if total_pnl is not None else None,
        "total_pnl_pct": (total_pnl / contributions * 100) if total_pnl is not None and contributions > 0 else None,
        "unrealized_pnl_idr": round(unrealized, 2),
        "realized_pnl_idr": round(realized_total, 2),
        "asset_cost_basis_idr": round(total_cost_basis, 2),
        "holdings": holdings_detail,
        "valuation_complete": valuation_complete,
        "valuation_warnings": missing_valuations,
        "market_data_warnings": market_data_warnings,
        "transaction_count": len(txs),
        "method": "Dasar modal rata-rata tertimbang; valuasi emas menggunakan harga jual kembali Pegadaian.",
    }


@app.get("/api/transactions")
def list_transactions(limit: int = 100):
    limit = min(max(limit, 1), 500)
    with connect() as db:
        rows = db.execute("SELECT * FROM transactions ORDER BY occurred_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
    return {"items": [dict(r) for r in rows]}


def _validate_transaction_sequence(txs: list[dict]) -> Optional[str]:
    """Pastikan setiap arus kas dan kuantitas aset tetap masuk akal secara kronologis."""
    cash_running = 0.0
    quantity_by_asset = {"GOLD": 0.0, "SPY": 0.0}
    for tx in txs:
        gross = _tx_gross_idr(tx)
        fee = float(tx.get("fee_idr", 0) or 0)
        typ, asset = tx["tx_type"], tx["asset"]
        if typ == "DEPOSIT":
            cash_running += gross
        elif typ == "WITHDRAW":
            if cash_running + 0.01 < gross:
                return f"Penarikan Rp{gross:,.0f} melebihi saldo kas portofolio yang tercatat. Catat setoran/saldo awal terlebih dahulu."
            cash_running -= gross
        elif typ == "BUY":
            cost = gross + fee
            if cash_running + 0.01 < cost:
                return f"Saldo kas portofolio tidak cukup untuk pembelian Rp{cost:,.0f}. Catat setoran modal terlebih dahulu, atau gunakan Saldo awal aset untuk kepemilikan yang sudah ada."
            cash_running -= cost
            quantity_by_asset[asset] += float(tx["quantity"])
        elif typ == "SELL":
            quantity = float(tx["quantity"])
            if quantity_by_asset[asset] + 1e-8 < quantity:
                return f"Jumlah {asset} yang dijual melebihi unit yang tercatat. Periksa transaksi atau saldo awal aset."
            quantity_by_asset[asset] -= quantity
            cash_running += gross - fee
        elif typ == "OPENING":
            quantity_by_asset[asset] += float(tx["quantity"])
        elif typ == "DIVIDEND":
            cash_running += gross - fee
        if cash_running < -0.01:
            return "Urutan transaksi membuat saldo kas menjadi negatif. Periksa tanggal dan nilai transaksi."
        if any(value < -1e-8 for value in quantity_by_asset.values()):
            return "Urutan transaksi membuat jumlah aset menjadi negatif. Periksa tanggal dan kuantitas transaksi."
    return None


@app.post("/api/transactions")
def create_transaction(data: TransactionInput):
    occurred_at = data.occurred_at or now_iso()
    # Harga transaksi adalah harga eksekusi yang dicatat pengguna, bukan harga quote saat ini.
    stored_price_unit = data.price_unit or ("GRAM" if data.asset == "GOLD" else "UNIT")
    unit_factor = 100.0 if data.asset == "GOLD" and stored_price_unit == "0.01G" else 1.0
    stored_unit_price = data.unit_price * unit_factor
    with connect() as db:
        cur = db.execute(
            """INSERT INTO transactions(occurred_at, tx_type, asset, quantity, unit_price, currency, fx_rate, fee_idr, amount_idr, memo, created_at, price_unit, unit_price_entered)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (occurred_at, data.tx_type, data.asset, data.quantity, stored_unit_price, data.currency,
             data.fx_rate, data.fee_idr, data.amount_idr, data.memo[:500], now_iso(), stored_price_unit, data.unit_price),
        )
        row_id = cur.lastrowid
        validation_error = _validate_transaction_sequence(_read_transactions(db))
        if validation_error:
            # Melempar exception membuat context manager membatalkan insert secara atomik.
            raise HTTPException(status_code=400, detail=validation_error)

    # Panggil penyedia data sesudah transaksi database selesai agar request eksternal
    # tidak menahan kunci tulis SQLite. Quote tidak diperlukan untuk validasi ledger.
    gold = latest_gold_rates()
    spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS)
    fx_quote = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS)
    fx_rate = fx_quote.get("price") if fx_quote.get("status") in ("ok", "stale") else None
    with connect() as db:
        txs = _read_transactions(db)
    portfolio = _calculate_portfolio(txs, gold, spy, fx_rate, fx_quote.get("status"))
    return {"ok": True, "id": row_id, "portfolio": portfolio}


@app.put("/api/transactions/{transaction_id}")
def update_transaction(transaction_id: int, data: TransactionInput):
    """Ubah transaksi dengan validasi ledger yang sama seperti saat membuatnya."""
    occurred_at = data.occurred_at or now_iso()
    stored_price_unit = data.price_unit or ("GRAM" if data.asset == "GOLD" else "UNIT")
    unit_factor = 100.0 if data.asset == "GOLD" and stored_price_unit == "0.01G" else 1.0
    stored_unit_price = data.unit_price * unit_factor
    with connect() as db:
        existing = db.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan.")
        db.execute(
            """UPDATE transactions
               SET occurred_at=?, tx_type=?, asset=?, quantity=?, unit_price=?, currency=?, fx_rate=?,
                   fee_idr=?, amount_idr=?, memo=?, price_unit=?, unit_price_entered=?
               WHERE id=?""",
            (occurred_at, data.tx_type, data.asset, data.quantity, stored_unit_price, data.currency,
             data.fx_rate, data.fee_idr, data.amount_idr, data.memo[:500], stored_price_unit,
             data.unit_price, transaction_id),
        )
        validation_error = _validate_transaction_sequence(_read_transactions(db))
        if validation_error:
            raise HTTPException(status_code=400, detail="Perubahan ditolak agar ledger tetap konsisten. " + validation_error)

    gold = latest_gold_rates()
    spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS)
    fx_quote = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS)
    fx_rate = fx_quote.get("price") if fx_quote.get("status") in ("ok", "stale") else None
    with connect() as db:
        txs = _read_transactions(db)
    portfolio = _calculate_portfolio(txs, gold, spy, fx_rate, fx_quote.get("status"))
    return {"ok": True, "id": transaction_id, "portfolio": portfolio}


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan.")
        db.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        validation_error = _validate_transaction_sequence(_read_transactions(db))
        if validation_error:
            raise HTTPException(
                status_code=400,
                detail="Penghapusan ini membuat riwayat transaksi tidak konsisten. " + validation_error,
            )
    return {"ok": True}


@app.get("/api/overview")
def overview(force_market: bool = False):
    gold = latest_gold_rates()
    spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS, force=force_market)
    fx = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS, force=force_market)
    with connect() as db:
        txs = _read_transactions(db)
        goals = [dict(r) for r in db.execute("SELECT * FROM goals ORDER BY id ASC").fetchall()]
        recent = [dict(r) for r in db.execute("SELECT * FROM transactions ORDER BY occurred_at DESC, id DESC LIMIT 8").fetchall()]
    pf = _calculate_portfolio(txs, gold, spy, fx.get("price") if fx.get("status") in ("ok", "stale") else None, fx.get("status"))
    return {"portfolio": pf, "market": {
        "gold": {"data": gold, "status": gold.get("freshness_status", "ok") if gold else "not_configured"},
        "spy": spy, "fx": fx,
    }, "goals": goals, "recent_transactions": recent, "generated_at": now_iso()}


class GoalInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    name: str = Field(min_length=1, max_length=100)
    target_idr: float = Field(gt=0)
    current_saved_idr: float = Field(default=0, ge=0)
    target_date: Optional[date] = None
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def normalize_goal(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Nama target tidak boleh kosong.")
        self.notes = self.notes.strip()
        return self


@app.get("/api/goals")
def list_goals():
    with connect() as db:
        rows = db.execute("SELECT * FROM goals ORDER BY id ASC").fetchall()
    return {"items": [dict(r) for r in rows]}


@app.post("/api/goals")
def create_goal(data: GoalInput):
    with connect() as db:
        cur = db.execute(
            "INSERT INTO goals(name,target_idr,current_saved_idr,target_date,notes,created_at) VALUES(?,?,?,?,?,?)",
            (data.name, data.target_idr, data.current_saved_idr, data.target_date.isoformat() if data.target_date else None, data.notes[:500], now_iso()),
        )
        row_id = cur.lastrowid
        row = db.execute("SELECT * FROM goals WHERE id = ?", (row_id,)).fetchone()
    return {"ok": True, "goal": dict(row)}


@app.put("/api/goals/{goal_id}")
def update_goal(goal_id: int, data: GoalInput):
    with connect() as db:
        cur = db.execute(
            "UPDATE goals SET name = ?, target_idr = ?, current_saved_idr = ?, target_date = ?, notes = ? WHERE id = ?",
            (data.name.strip(), data.target_idr, data.current_saved_idr, data.target_date.isoformat() if data.target_date else None, data.notes[:500], goal_id),
        )
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Target tidak ditemukan.")
        row = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return {"ok": True, "goal": dict(row)}


@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: int):
    with connect() as db:
        cur = db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Target tidak ditemukan.")
    return {"ok": True}


def _safe_csv_text(value) -> str:
    """Cegah teks bebas diperlakukan sebagai formula saat dibuka di aplikasi spreadsheet."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


@app.get("/api/export/transactions.csv")
def export_transactions_csv():
    """Ekspor ledger transaksi; berkas berisi data pribadi sehingga tetap hanya lokal."""
    with connect() as db:
        rows = db.execute("SELECT * FROM transactions ORDER BY occurred_at ASC, id ASC").fetchall()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([
        "ID", "Tanggal", "Jenis transaksi", "Aset", "Kuantitas", "Harga tersimpan per unit",
        "Harga yang dimasukkan", "Satuan harga", "Mata uang", "Kurs IDR per USD",
        "Biaya IDR", "Jumlah IDR", "Catatan",
    ])
    for row in rows:
        item = dict(row)
        writer.writerow([
            item["id"], item["occurred_at"], item["tx_type"], item["asset"], item["quantity"],
            item["unit_price"], item.get("unit_price_entered"), item.get("price_unit"), item["currency"],
            item["fx_rate"], item["fee_idr"], item["amount_idr"], _safe_csv_text(item["memo"]),
        ])
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="wealthpilot-transaksi.csv"'},
    )


@app.get("/api/export/backup.json")
def export_backup_json():
    """Ekspor cadangan data aplikasi tanpa API key atau kredensial provider."""
    tables = ("transactions", "goals", "pegadaian_rates", "market_snapshots", "market_bars")
    payload = {
        "application": "WealthPilot",
        "backup_version": 1,
        "exported_at": now_iso(),
        "notes": "Cadangan data lokal; tidak menyertakan file .env atau kunci API.",
        "tables": {},
    }
    with connect() as db:
        for table in tables:
            # Tabel market_bars menggunakan kunci primer gabungan, bukan kolom id.
            ordering = "datetime ASC" if table == "market_bars" else "id ASC"
            rows = db.execute(f"SELECT * FROM {table} ORDER BY {ordering}").fetchall()
            payload["tables"][table] = [dict(row) for row in rows]
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    filename = f"wealthpilot-cadangan-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok", "app": "WealthPilot", "db": str(DB_PATH.name),
        "twelve_data_configured": bool(API_KEY),
        "market_quote_interval": SPY_QUOTE_INTERVAL,
        "series_cache_seconds": SPY_SERIES_CACHE_SECONDS,
        "gold_rate_configured": latest_gold_rates() is not None,
        "timestamp": now_iso(),
    }
