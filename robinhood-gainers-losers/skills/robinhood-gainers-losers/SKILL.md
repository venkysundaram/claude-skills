---
name: robinhood-gainers-losers
description: Fetch and display performance of holdings in your Robinhood portfolio. Use this skill whenever the user asks to see how their portfolio is performing, which holdings are up/down today, or wants to check personal portfolio movers on Robinhood. Supports time range filtering (1 day, 1 week, 1 month) and displays results as separate tables per account. Shows symbol, current price, % change, absolute change, and position value. Useful for quick portfolio health check, identifying top/worst performers in personal holdings.
---

# Robinhood Portfolio Gainers & Losers

## Overview

Shows which of the user's **own** Robinhood holdings are up or down over 1 day, 1 week or 1 month, as separate tables per account. This is about the user's positions only, not market-wide movers. The skill is **read-only**: never place, modify or cancel orders while running it.

Claude fetches the data with the Robinhood MCP tools; `scripts/compute_gainers_losers.py` does all of the math and formatting. Don't compute percentages by hand.

## When to Use

- "How is my portfolio doing today?"
- "What's up and down in my Robinhood holdings?"
- "Show my gainers and losers for the past week / month"
- "Break down my gains and losses by account"
- "What's down the most in my portfolio?" / "Top 5 gainers today"
- "How are my crypto holdings doing today?"

## Parameters to Extract

| Parameter | Values | Default |
|---|---|---|
| `time_range` | `1day`, `1week`, `1month` ("today" → 1day, "this week" → 1week, "past month" → 1month) | `1day` |
| `asset_class` | `stocks`, `crypto`, `both` | `both` |
| `limit` | rows per category per account | `15` |
| accounts | all accounts, or the one the user names | all |

A request about "my portfolio" or "my holdings" means **all** of the user's accounts: use every account returned by `get_accounts`. If the user names one account ("my IRA"), use only that one.

## Workflow

1. **Accounts** — call `get_accounts`. For each account keep its display name, `account_number` (for equities) and numeric `rhs_account_number` (for crypto). Do not use `rhc_account_number`; it returns no positions.

2. **Positions** — per account:
   - Stocks: `get_equity_positions(account_number=...)`.
   - Crypto: `get_crypto_positions(rhs_account_number=...)`.
   - Both are paginated: while the response has a `next` cursor, call again with `cursor=<next>`.
   - Skip whichever asset class the user didn't ask for.

3. **Current prices and 1-day reference** — collect the unique symbols across all accounts.
   - Stocks: `get_equity_quotes(symbols=[...])` in batches of **at most 20**. Above 20, previous closes are omitted. Use the last trade price as `price` and the last completed session close as the 1-day `reference_price`.
   - Crypto: `get_crypto_quotes(symbols=["BTC-USD", ...])`. Use the mark price as `price` and the previous close (`open_price`) as the 1-day `reference_price`. Pass `timezone` only if the user's timezone is known.

4. **Week / month reference (stocks only)**
   - Get `start_time` by running `python3 scripts/compute_gainers_losers.py --period-start 1week` (or `1month`).
   - Call `get_equity_historicals(symbols=[...], start_time=<that>, interval="day")` in batches of **at most 10** symbols.
   - Put each symbol's bars in `daily_bars` as `{"date", "close"}`; the script picks the close before the period start.
   - There is **no crypto historicals tool**. For week/month, leave crypto `reference_price` empty; the script shows it as "not included" with a reason, but still counts its value.

5. **Compute and render** — write a JSON file (shape documented at the top of the script and in `references/implementation.md`) to a temp location and run:
   ```bash
   python3 scripts/compute_gainers_losers.py --input /tmp/rh_portfolio.json
   ```
   Show the Markdown output to the user as-is.

6. **Summarize** — after the tables, add one or two sentences: the biggest mover in each direction and anything that was "not included" and why.

## Output

One section per account (a single "My Holdings" set when there's only one account), each with total value, total change for the period, and Gainers / Losers tables:

| Symbol | Qty | Price | % Change | $ Change / Share | Position Change | Position Value |
|---|---|---|---|---|---|---|

Gainers are sorted by % change descending, losers ascending (worst first). Unchanged and unavailable holdings are listed below the tables rather than silently dropped. Account numbers are masked to their last 4 digits.

## Limitations

- No crypto history is available through the Robinhood tools, so crypto week/month changes are reported as N/A.
- 1-day stock changes compare against the last regular-session close; extended-hours moves are reflected only in the current price.
- Options positions are not included.

## Next Steps to Offer

- Technicals or fundamentals for a big mover (`get_equity_technical_indicators`, `get_equity_fundamentals`)
- Price alerts on top movers (`create_alert`, only if the user asks)
- Realized P&L or tax lots (`get_realized_pnl`, `get_equity_tax_lots`)
