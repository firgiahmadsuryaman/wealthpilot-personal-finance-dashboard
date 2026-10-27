# WealthPilot — Personal Wealth Dashboard

[![Tests](https://img.shields.io/badge/tests-unittest-informational)](https://docs.python.org/3/library/unittest.html)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/database-SQLite-003B57)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A local-first financial dashboard that keeps invested capital separate from market value and profit/loss.** WealthPilot is built for users who want to track a portfolio, monitor market quotes, record cash flows, and manage their own financial goals without pretending that unavailable prices are real-time data.

> The UI is Indonesian-first. The app is a personal portfolio project and is not affiliated with Pegadaian, Pluang, or Twelve Data.

## Why this project exists

A portfolio's current market value is not the same as the money contributed. WealthPilot keeps the transaction ledger as the source of truth and presents separate figures for net contributions, current portfolio value, cash balance, realized P/L, and unrealized P/L. It also makes market-data limitations visible instead of silently filling missing quotes with zero.

## Features

- **Portfolio accounting:** separates external deposits/withdrawals from internal asset buys/sells.
- **Transaction ledger:** records opening balances, buys, sells, fees, and cash income.
- **Pegadaian Tabungan Emas tracking:** stores customer-buy and customer-sell/buyback price snapshots copied from Tring! by Pegadaian; valuation uses the customer sell-back price.
- **SPY and USD/IDR quote integration:** uses Twelve Data when an API key and suitable market-data permission are configured.
- **Market monitor:** displays quote source/status and timestamps, plus stored quote history.
- **Custom financial goals:** create, edit, and delete goals with your own name, target amount, initial progress, and target date.
- **Cash flow and portfolio allocation:** presents the recorded investment account's cash activity and asset distribution.
- **Local-first storage:** transaction data is stored in SQLite on the local machine.
- **Tests and CI:** accounting unit tests and API tests for custom-goal CRUD, with a GitHub Actions workflow.

## Data integrity by design

| Data | How WealthPilot handles it |
|---|---|
| Net contributions | Derived from external deposits, imported opening positions, and external withdrawals; market changes do not alter contributions. |
| Portfolio value | Portfolio cash plus the latest available valuation of holdings. If a price is missing, valuation remains incomplete rather than assuming zero. |
| Gold value | Uses the Tabungan Emas Pegadaian customer sell-back price captured from Tring!, not a global spot-gold quote or another gold product's price. |
| SPY value | Uses the provider's SPY quote and USD/IDR rate; it can differ from Pluang's execution price and transaction FX rate. |
| Realized P/L | Calculated when a holding is sold, using the MVP's weighted-average cost-basis convention. |
| Unrealized P/L | Current holding valuation minus remaining cost basis. |
| Financial goals | User-defined planning records; progress is manual and separate from bank accounts and portfolio assets. |
| Data freshness | Provider quote timestamp and source status are shown when available. Polling does not mean tick-by-tick streaming. |

## Technology stack

- **Backend:** Python, FastAPI, Pydantic, HTTPX
- **Database:** SQLite
- **Frontend:** HTML, CSS, vanilla JavaScript
- **Market data:** Twelve Data API for SPY and USD/IDR quotes
- **Testing:** Python `unittest` and FastAPI's test client
- **Automation:** GitHub Actions

## Architecture

```text
Browser (HTML / CSS / JavaScript)
              |
              | same-origin JSON requests
              v
      FastAPI application
       |       |       |
       |       |       +---- Twelve Data API (SPY, USD/IDR)
       |       |
       |       +------------ Manual Tring! Pegadaian price snapshots
       |
       +-------------------- SQLite transaction ledger and goals
```

See [Architecture](docs/ARCHITECTURE.md) for the routes and accounting conventions.

## Quick start — Windows

1. Install Python 3.10 or newer.
2. Download or clone this repository, then open the project folder in PowerShell.
3. Run `run.bat`. The script creates a virtual environment, installs dependencies, and copies `.env.example` to `.env` if needed.
4. Open **http://127.0.0.1:8000** in your browser.
5. To enable SPY and USD/IDR quotes, add your key to `.env`:

   ```dotenv
   TWELVE_DATA_API_KEY=replace_with_your_own_key
   SPY_CACHE_SECONDS=180
   USDIDR_CACHE_SECONDS=900
   ```

6. Restart the app after editing `.env`.
7. In **Pengaturan data**, enter the customer-buy and customer-sell values currently shown in Tring! by Pegadaian, choose the correct quote unit (per gram or per 0.01 gram), and save the timestamp.
8. Enter opening positions and actual transactions from your records before interpreting portfolio numbers.

### Run manually

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If PowerShell says `.env` already exists, do not overwrite your existing key; edit it directly. Stop the server with `Ctrl+C`.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

The tests use synthetic values only inside isolated test cases and temporary databases; they do not seed sample holdings into your live application database.

## Important data-source limitations

### Pegadaian / Tring!

The current version **does not automatically connect to your Pegadaian account**. It has not verified a documented public API that can read a personal Tabungan Emas balance and account-specific prices. To keep the valuation aligned with the actual product, copy the customer-buy and customer-sell values from Tring! and save a timestamp. Pegadaian pricing may update periodically and is not guaranteed to change every second.

### SPY / USD/IDR

Provider quotes require a Twelve Data API key and a subscription/license that allows the required instruments, freshness, and display use. The app polls and uses a server-side cache; it is not a direct exchange feed or tick-by-tick streaming application. A provider quote is not guaranteed to equal Pluang's execution price, and displayed values can be delayed based on provider plan and market rules.

Before exposing the dashboard to other users, verify the provider's latest data-redistribution and display license. Do not redistribute market data just because an API endpoint is technically accessible.

## Security and privacy

- The app binds to `127.0.0.1` by default and is intended for local use.
- Keep `.env`, API keys, SQLite databases, logs, and account-specific screenshots out of Git.
- Never enter Pegadaian or Pluang passwords, PINs, OTPs, session cookies, or authentication tokens into WealthPilot.
- Do not expose the server publicly without authentication, authorization, HTTPS, rate limiting, backup, and security review.
- This project is an educational portfolio tool, not financial advice or an execution platform.

Read [SECURITY.md](SECURITY.md) for additional precautions.

## Roadmap

- [x] Keep contribution capital separate from market-based valuation.
- [x] Transaction ledger and weighted-average cost basis for sales.
- [x] Manual Pegadaian quote snapshots with source unit and timestamp.
- [x] Provider-backed SPY and USD/IDR quote path.
- [x] User-defined financial goals with create, update, and delete.
- [x] Automated accounting and goal API tests.
- [ ] CSV import/export with reconciliation checks.
- [ ] Editable transaction corrections with audit history.
- [ ] Optional target contribution planner and scenario simulation.
- [ ] Add authentication before any multi-user or hosted deployment.
- [ ] Investigate an official Pegadaian data integration if one becomes available and permitted.

## Project portfolio notes

For product scope and success criteria, see [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md); for the component map and API routes, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). For a ready-to-use GitHub description, repository topics, LinkedIn project summary, and a post draft in Indonesian, see [docs/PORTFOLIO_GUIDE_ID.md](docs/PORTFOLIO_GUIDE_ID.md). Also see [CHANGELOG.md](CHANGELOG.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Distributed under the [MIT License](LICENSE).
