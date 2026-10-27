# Product Brief — WealthPilot

## Product statement

WealthPilot is a local-first personal wealth dashboard designed to help people—especially freelancers with irregular income—understand what they contributed, what their assets are worth now, and whether their financial goals are progressing.

## Primary user

A single user managing personal investments, recurring and irregular income, cash reserve needs, and more than one financial goal. The first release is local-first and is not a multi-user SaaS.

## Main user problems

1. Contributions are easily confused with market gains or losses.
2. Price changes are hard to interpret without seeing the data source and timestamp.
3. Irregular income makes a fixed monthly investment plan unrealistic.
4. Goals are difficult to track if they are tied to fixed templates rather than the user's priorities.
5. A missing quote must not be treated as a zero-value asset.

## Product principles

- Keep external cash flows distinct from internal asset transactions.
- Treat the transaction ledger as the basis for accounting calculations.
- Show modal, current market value, realized P/L, and unrealized P/L separately.
- Display a data source and timestamp where available.
- Do not label prices as guaranteed real-time unless the source and licence support it.
- Do not fabricate values when a market source is unavailable.
- Let the user create goals with any name, target amount, initial saved amount, notes, and optional target date.
- Keep planning goals separate from actual bank balances and investment holdings until an explicit reconciliation feature is implemented.
- Never request credentials, PINs, OTPs, or session tokens for Pegadaian or Pluang.

## Current scope

- Record deposits, withdrawals, opening positions, buys, sells, fees, and cash income.
- Calculate portfolio cash, net contributions, holdings, current valuation when quotes are available, and profit/loss.
- Store user-entered Pegadaian Tabungan Emas price snapshots from Tring! by Pegadaian.
- Retrieve SPY and USD/IDR quote data through a configured market-data provider.
- View recorded quote history and timestamps.
- Create, update, list, and delete custom financial goals.
- Review cash-flow history and portfolio allocation.

## Not in current scope

- Automated login or balance sync with Tring! or Pluang.
- Guaranteed tick-by-tick market streaming.
- Order placement, trade execution, or automatic buy/sell decisions.
- Multi-user accounts, cloud storage, or hosted financial-data processing.
- Automatic reconciliation of a goal's saved amount with bank balances or portfolio holdings.
- Investment return guarantees or personalized regulated financial advice.

## Data source contract

### Tabungan Emas Pegadaian

The user manually captures the customer-buy price and customer sell-back/buyback price shown in Tring!, the exact unit, and the capture time. Valuation uses the customer sell-back price. The snapshot represents a recorded quote, not a continuous feed or necessarily an executable price for every account at every moment.

### SPY and USD/IDR

The app retrieves provider quotes only when a valid API key is configured and the selected plan supports the instruments, freshness, and display use. The app uses polling and caching; the provider timestamp and plan govern quote freshness. Provider price and USD/IDR conversion are estimates, not guarantees of a Pluang execution price or transaction FX rate.

## Success criteria for the MVP

- A new installation contains no fabricated holdings or price snapshots.
- Unit tests prove that missing valuation data does not become zero valuation.
- Unit tests prove that modal and portfolio value stay distinct.
- The user can create and edit a generic goal without any hard-coded goal category.
- The UI distinguishes a source quote from manual input and records timestamps.
- The README explains setup, data-source limitations, accounting rules, and safe local use.
