# Architecture

WealthPilot uses a small local-first architecture so the data model and financial calculations stay understandable and auditable.

```text
Browser (HTML / CSS / vanilla JavaScript)
             |
             | JSON over same-origin HTTP
             v
FastAPI application (app/main.py)
   |             |                 |
   |             |                 +--> Twelve Data API (SPY and USD/IDR quotes)
   |             |
   |             +--> Manual Pegadaian rate snapshots copied from Tring!
   |
   +--> SQLite ledger (data/wealthpilot.db)
```

## Main responsibilities

- **Frontend:** displays market quote status, timestamps, portfolio summaries, transaction ledger, cash flow, custom goals, and provider settings.
- **FastAPI:** validates transaction and goal payloads, serves quote/history endpoints, and coordinates portfolio calculations.
- **SQLite:** stores user-entered transactions, Pegadaian quote snapshots, custom goals, and market history.
- **Twelve Data:** retrieves SPY and USD/IDR quotes when an API key is configured and the chosen subscription permits the required market data.
- **Pegadaian/Tring!:** current release uses manually entered buyback and customer-buy values to avoid pretending that an undocumented account API is available.

## API overview

| Route | Purpose |
|---|---|
| `GET /api/health` | Local app and data-source configuration status |
| `GET /api/overview` | Portfolio summary, market data, goals, and recent transactions |
| `GET /api/market` | Current quote summary |
| `POST /api/market/pegadaian` | Save a user-captured Pegadaian price snapshot |
| `GET /api/market/pegadaian/history` | Retrieve Pegadaian price history |
| `GET /api/market/history/{symbol}` | Retrieve stored market quote history |
| `GET /api/transactions` | List ledger entries |
| `POST /api/transactions` | Validate and record a ledger entry |
| `DELETE /api/transactions/{id}` | Delete an entry only if the remaining ledger stays valid |
| `GET /api/goals` | List user-defined financial goals |
| `POST /api/goals` | Create a custom goal |
| `PUT /api/goals/{id}` | Update a custom goal |
| `DELETE /api/goals/{id}` | Delete a custom goal |

## Accounting conventions

- External contributions and withdrawals are kept separate from internal asset purchases and sales.
- Asset valuation uses the latest applicable quote available to the app; missing prices remain missing rather than being silently treated as zero.
- Pegadaian gold is valued using the manually captured customer sell-back/buyback price, not the global spot price.
- SPY is valued using the provider quote and USD/IDR rate; this is not guaranteed to equal the execution price or FX rate at Pluang.
- Realized profit/loss is calculated using the weighted-average cost basis used by this MVP.
- Goal progress is manually maintained and is intentionally separate from investment holdings and bank balances.

## Market refresh semantics

The browser refreshes dashboard data periodically, while provider quote caching reduces repeated upstream requests. This is polling, not tick-by-tick streaming. Pegadaian snapshots update only when the user enters a new quote from Tring!. The interface should not describe these values as guaranteed live prices unless the provider and licence explicitly support that level of freshness.
