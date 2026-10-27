from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "wealthpilot.db"
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
SPY_CACHE_SECONDS = max(30, int(os.getenv("SPY_CACHE_SECONDS", "180")))
USDIDR_CACHE_SECONDS = max(60, int(os.getenv("USDIDR_CACHE_SECONDS", "900")))

app = FastAPI(title="WealthPilot", version="0.2.0", description="Personal investment dashboard; local-first MVP")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

_quote_cache: dict[str, dict] = {}
_quote_cache_time: dict[str, float] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
                source TEXT NOT NULL
            );
            """
        )
        # Safe small migrations for a database created by an earlier MVP build.
        tx_columns = {row[1] for row in db.execute("PRAGMA table_info(transactions)").fetchall()}
        if "price_unit" not in tx_columns:
            db.execute("ALTER TABLE transactions ADD COLUMN price_unit TEXT NOT NULL DEFAULT 'UNIT'")
        if "unit_price_entered" not in tx_columns:
            db.execute("ALTER TABLE transactions ADD COLUMN unit_price_entered REAL")
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


# ---------- Market data ----------

def _quote_from_twelvedata(symbol: str, ttl: int) -> dict:
    """Fetch a quote from Twelve Data. All provider data remains labeled with its source/timestamp."""
    if not API_KEY:
        return {
            "status": "not_configured",
            "symbol": symbol,
            "message": "TWELVE_DATA_API_KEY belum diisi di file .env.",
            "source": "Twelve Data",
            "price": None,
            "timestamp": None,
        }
    now = time.time()
    if symbol in _quote_cache and now - _quote_cache_time.get(symbol, 0) < ttl:
        return dict(_quote_cache[symbol], cache_status="cached")
    try:
        response = httpx.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": symbol, "apikey": API_KEY},
            timeout=12.0,
            headers={"User-Agent": "WealthPilot/0.1 personal-dashboard"},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "error" or data.get("code"):
            message = data.get("message") or data.get("description") or "Penyedia data mengembalikan error."
            return {
                "status": "error", "symbol": symbol, "message": message,
                "source": "Twelve Data", "price": None,
                "timestamp": now_iso(),
            }
        price_value = data.get("close") or data.get("price") or data.get("last")
        price = float(price_value) if price_value not in (None, "") else None
        result = {
            "status": "ok" if price is not None else "error",
            "symbol": symbol,
            "price": price,
            "currency": data.get("currency") or ("USD" if symbol == "SPY" else "IDR"),
            "change": _to_float(data.get("change")),
            "percent_change": _to_float(data.get("percent_change")),
            "previous_close": _to_float(data.get("previous_close")),
            "timestamp": data.get("datetime") or data.get("timestamp") or now_iso(),
            "market_open": data.get("is_market_open"),
            "source": "Twelve Data",
            "cache_status": "fresh",
            "message": None if price is not None else "Harga tidak ada dalam respons provider.",
        }
        _quote_cache[symbol] = result
        _quote_cache_time[symbol] = now
        if result.get("price") is not None:
            try:
                with connect() as db:
                    last = db.execute("SELECT timestamp, price FROM market_snapshots WHERE symbol=? ORDER BY id DESC LIMIT 1", (symbol,)).fetchone()
                    if not last or last["timestamp"] != str(result.get("timestamp")):
                        db.execute(
                            "INSERT INTO market_snapshots(symbol, price, percent_change, timestamp, source) VALUES(?,?,?,?,?)",
                            (symbol, result["price"], result.get("percent_change"), str(result.get("timestamp") or now_iso()), "Twelve Data"),
                        )
            except sqlite3.Error:
                pass
        return result
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        # Stale quote can be shown but is always marked stale; no fabricated price is substituted.
        if symbol in _quote_cache:
            return dict(_quote_cache[symbol], status="stale", cache_status="stale", message=f"Gagal memperbarui quote: {exc}")
        return {
            "status": "error", "symbol": symbol, "price": None,
            "timestamp": now_iso(), "source": "Twelve Data",
            "message": f"Tidak dapat mengambil data: {exc}",
        }


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
    latest["sellback_change_pct"] = None
    if prev and prev["customer_sell_idr_g"]:
        latest["sellback_change_pct"] = (row["customer_sell_idr_g"] / prev["customer_sell_idr_g"] - 1) * 100
    latest["source_url"] = "https://pegadaian.co.id/harga-emas"
    return latest


@app.get("/api/market")
def get_market():
    gold = latest_gold_rates()
    spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS)
    fx = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS)
    if fx.get("status") == "ok" and fx.get("price"):
        fx_rate = fx["price"]
    else:
        fx_rate = None
    return {
        "gold": {
            "status": "ok" if gold else "not_configured",
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
    customer_buy_price: float = Field(gt=0, description="Harga beli persis seperti yang terlihat di Tring!")
    customer_sell_price: float = Field(gt=0, description="Harga jual kembali persis seperti yang terlihat di Tring!")
    quote_unit: Literal["GRAM", "0.01G"] = "0.01G"
    captured_at: Optional[str] = None
    source: str = "Tring! by Pegadaian (input manual)"
    notes: str = ""

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


@app.get("/api/market/history/{symbol}")
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
    memo: str = ""

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
        return self


def _read_transactions(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT * FROM transactions ORDER BY occurred_at ASC, id ASC").fetchall()
    return [dict(r) for r in rows]


def _tx_gross_idr(tx: dict) -> float:
    if tx["tx_type"] in ("DEPOSIT", "WITHDRAW", "DIVIDEND"):
        return float(tx["amount_idr"])
    rate = float(tx["fx_rate"] or 1) if tx["currency"] == "USD" else 1.0
    return float(tx["quantity"]) * float(tx["unit_price"]) * rate


def _calculate_portfolio(txs: list[dict], gold: Optional[dict], spy: dict, fx_rate: Optional[float]) -> dict:
    holdings = {
        "GOLD": {"quantity": 0.0, "cost_basis_idr": 0.0, "realized_pnl_idr": 0.0},
        "SPY": {"quantity": 0.0, "cost_basis_idr": 0.0, "realized_pnl_idr": 0.0},
    }
    cash = 0.0
    contributions = 0.0
    realized_total = 0.0
    ledger = []
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
        ledger.append({"id": tx["id"], "tx_type": typ, "asset": asset, "gross_idr": gross, "fee_idr": fee, "realized_pnl_idr": pnl})

    gold_current_price = float(gold["customer_sell_idr_g"]) if gold else None
    spy_price = spy.get("price") if spy.get("status") == "ok" else None
    gold_value = holdings["GOLD"]["quantity"] * gold_current_price if gold_current_price is not None else None
    fx = float(fx_rate) if fx_rate else None
    spy_value = holdings["SPY"]["quantity"] * float(spy_price) * fx if spy_price is not None and fx is not None else None
    unrealized = 0.0
    missing_valuations = []
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
    has_gold = gold_value is not None
    has_spy = spy_value is not None
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
        "transaction_count": len(txs),
        "method": "Dasar modal rata-rata tertimbang; valuasi emas menggunakan harga jual kembali Pegadaian.",
    }


@app.get("/api/transactions")
def list_transactions(limit: int = 100):
    limit = min(max(limit, 1), 500)
    with connect() as db:
        rows = db.execute("SELECT * FROM transactions ORDER BY occurred_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.post("/api/transactions")
def create_transaction(data: TransactionInput):
    occurred_at = data.occurred_at or now_iso()
    # Use recorded execution values; quotes are not substituted as if they were actual fills.
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
        # Validate the full transaction sequence after insertion. Reject impossible sells / cash-outs.
        txs = _read_transactions(db)
        gold = latest_gold_rates()
        spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS)
        fx_quote = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS)
        pf = _calculate_portfolio(txs, gold, spy, fx_quote.get("price") if fx_quote.get("status") == "ok" else None)
        # Check a sell was actually covered at its point in sequence.
        qty_by_asset = {"GOLD": 0.0, "SPY": 0.0}
        cash_running = 0.0
        validation_error = None
        for tx in txs:
            gross = _tx_gross_idr(tx)
            fee = float(tx.get("fee_idr", 0) or 0)
            typ, asset = tx["tx_type"], tx["asset"]
            if typ == "DEPOSIT": cash_running += gross
            elif typ == "WITHDRAW":
                if cash_running + 0.01 < gross:
                    validation_error = f"Penarikan Rp{gross:,.0f} melebihi saldo kas portofolio yang tercatat. Catat setoran/saldo awal terlebih dahulu."
                    break
                cash_running -= gross
            elif typ == "BUY":
                cost = gross + fee
                if cash_running + 0.01 < cost:
                    validation_error = f"Saldo kas portofolio tidak cukup untuk pembelian Rp{cost:,.0f}. Catat setoran modal terlebih dahulu, atau gunakan Saldo awal aset untuk kepemilikan yang sudah ada."
                    break
                cash_running -= cost
                qty_by_asset[asset] += float(tx["quantity"])
            elif typ == "SELL":
                if qty_by_asset[asset] + 1e-8 < float(tx["quantity"]):
                    validation_error = f"Jumlah {asset} yang dijual melebihi unit yang tercatat. Periksa transaksi atau saldo awal aset."
                    break
                qty_by_asset[asset] -= float(tx["quantity"])
                cash_running += gross - fee
            elif typ == "OPENING":
                qty_by_asset[asset] += float(tx["quantity"])
            elif typ == "DIVIDEND":
                cash_running += gross - fee
        if validation_error:
            db.execute("DELETE FROM transactions WHERE id = ?", (row_id,))
            raise HTTPException(status_code=400, detail=validation_error)
    return {"ok": True, "id": row_id, "portfolio": pf}


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan.")
        db.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        txs = _read_transactions(db)
        # Validate remaining history remains feasible.
        cash_running = 0.0
        qty = {"GOLD": 0.0, "SPY": 0.0}
        for tx in txs:
            gross, fee, typ, asset = _tx_gross_idr(tx), float(tx["fee_idr"] or 0), tx["tx_type"], tx["asset"]
            if typ == "DEPOSIT": cash_running += gross
            elif typ == "WITHDRAW": cash_running -= gross
            elif typ == "BUY": cash_running -= gross + fee; qty[asset] += tx["quantity"]
            elif typ == "SELL": qty[asset] -= tx["quantity"]; cash_running += gross - fee
            elif typ == "OPENING": qty[asset] += tx["quantity"]
            elif typ == "DIVIDEND": cash_running += gross - fee
            if cash_running < -0.01 or qty.get(asset, 0) < -1e-8:
                raise HTTPException(status_code=400, detail="Penghapusan ini membuat urutan transaksi tidak konsisten. Tambahkan transaksi penyesuaian, jangan hapus transaksi ini.")
    return {"ok": True}


@app.get("/api/overview")
def overview():
    gold = latest_gold_rates()
    spy = _quote_from_twelvedata("SPY", SPY_CACHE_SECONDS)
    fx = _quote_from_twelvedata("USD/IDR", USDIDR_CACHE_SECONDS)
    with connect() as db:
        txs = _read_transactions(db)
        goals = [dict(r) for r in db.execute("SELECT * FROM goals ORDER BY id ASC").fetchall()]
        recent = [dict(r) for r in db.execute("SELECT * FROM transactions ORDER BY occurred_at DESC, id DESC LIMIT 8").fetchall()]
    pf = _calculate_portfolio(txs, gold, spy, fx.get("price") if fx.get("status") == "ok" else None)
    return {"portfolio": pf, "market": {
        "gold": {"data": gold, "status": "ok" if gold else "not_configured"},
        "spy": spy, "fx": fx,
    }, "goals": goals, "recent_transactions": recent, "generated_at": now_iso()}


class GoalInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_idr: float = Field(gt=0)
    current_saved_idr: float = Field(default=0, ge=0)
    target_date: Optional[str] = None
    notes: str = ""

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
            (data.name, data.target_idr, data.current_saved_idr, data.target_date, data.notes[:500], now_iso()),
        )
        row_id = cur.lastrowid
        row = db.execute("SELECT * FROM goals WHERE id = ?", (row_id,)).fetchone()
    return {"ok": True, "goal": dict(row)}


@app.put("/api/goals/{goal_id}")
def update_goal(goal_id: int, data: GoalInput):
    with connect() as db:
        cur = db.execute(
            "UPDATE goals SET name = ?, target_idr = ?, current_saved_idr = ?, target_date = ?, notes = ? WHERE id = ?",
            (data.name.strip(), data.target_idr, data.current_saved_idr, data.target_date, data.notes[:500], goal_id),
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


@app.get("/api/health")
def health():
    return {
        "status": "ok", "app": "WealthPilot", "db": str(DB_PATH.name),
        "twelve_data_configured": bool(API_KEY),
        "gold_rate_configured": latest_gold_rates() is not None,
        "timestamp": now_iso(),
    }
