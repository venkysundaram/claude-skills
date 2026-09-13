---
name: robinhood-gainers-losers
description: Fetch and display performance of holdings in your Robinhood portfolio. Use this skill whenever the user asks to see how their portfolio is performing, which holdings are up/down today, or wants to check personal portfolio movers on Robinhood. Supports time range filtering (1 day, 1 week, 1 month) and displays results as separate tables per account. Shows symbol, current price, % change, absolute change, and position value. Useful for quick portfolio health check, identifying top/worst performers in personal holdings.
---

# Robinhood Portfolio Gainers & Losers

## Overview

This skill retrieves your Robinhood portfolio holdings across all accounts and displays their intraday/period performance, organized by account. Shows which of YOUR positions are up/down by percentage and dollar amount.

## When to Use

Trigger this skill when the user wants to:
- See how their Robinhood portfolio is performing today
- Check which of their holdings are gainers vs losers
- Get a personal portfolio health snapshot
- Review performance by account (if holding multiple accounts)
- Identify top performers and worst performers within their own positions

## Usage

### Basic Query
```
"Show me my portfolio performance today"
"How are my Robinhood holdings doing?"
"What's up and down in my portfolio?"
"Show me my personal gainers and losers"
```

### With Options
```
"Show me my portfolio gains for the past week"
"What's my worst performer this month?"
"Break down my gains/losses by account"
"Show me my top 5 gainers and losers today"
```

## Workflow

1. **Fetch portfolio accounts**: Call `Robinhood:get_accounts` to retrieve all linked Robinhood accounts.
2. **Get holdings per account**: For each account, call `Robinhood:get_equity_positions` (stocks) and `Robinhood:get_crypto_positions` (crypto) to retrieve user's current holdings.
3. **Determine time range**: Extract or ask for time range preference (1 day / 1 week / 1 month). Default to 1 day if not specified.
4. **Fetch current quotes**: Call `Robinhood:get_equity_quotes` and `Robinhood:get_crypto_quotes` for all held symbols to get current prices and % changes.
5. **Calculate performance**: For each holding, compute % change and $ change using current price vs open price (1 day) or historical open (week/month).
6. **Organize by account**: Group holdings by account, then sort each group by % change (gainers descending, losers ascending).
7. **Display**: Render separate tables per account with:
   - Symbol/Ticker
   - Quantity Held
   - Current Price
   - % Change (colored: green for gainers, red for losers)
   - Absolute Change ($ or currency)
   - Total Position Value

## Data Structure

Results should be organized by account (if multiple) with separate gainers/losers tables:

```
## ACCOUNT 1: Main Brokerage

### Holdings - Gainers
Symbol | Qty | Price | % Change | $ Change | Position Value

### Holdings - Losers
Symbol | Qty | Price | % Change | $ Change | Position Value

## ACCOUNT 2: IRA / Alternate Account

### Holdings - Gainers
Symbol | Qty | Price | % Change | $ Change | Position Value

### Holdings - Losers
Symbol | Qty | Price | % Change | $ Change | Position Value
```

If only one account exists, show a single set of tables labeled simply as "My Holdings — Gainers" and "My Holdings — Losers".

## Limitations & Notes

- **Time range filtering**: Robinhood API provides real-time quotes. For intraday % changes, we compare current price to prior close. For weekly/monthly % changes, we may need to fetch historical pricing data (`Robinhood:get_equity_historicals` or `Robinhood:get_crypto_quotes` with date range).
- **Count**: Default to top 10-15 per category. User can request larger counts (e.g., "top 25 gainers").
- **Crypto vs. Equities**: Use `get_equity_quotes` for stocks and `get_crypto_quotes` for crypto. Results are presented separately if needed.
- **Real-time vs. Delayed**: Robinhood provides real-time data for authenticated users.

## Implementation Notes

### For 1 Day Changes
Use current intraday % change directly from quote data.

### For 1 Week or 1 Month Changes
Fetch historical OHLC data using `Robinhood:get_equity_historicals` or `Robinhood:get_crypto_historicals` and calculate:
```
% change = ((current price - open price) / open price) × 100
```

Or fetch the price from the start of the period and compare to current.

### Presentation Format

Use Markdown tables for clarity:

```markdown
## Top Gainers (1 Day)

| Symbol | Price | % Change | $ Change |
|--------|-------|----------|----------|
| NVDA   | $145.20 | +5.32% | +7.35 |
| TSLA   | $238.50 | +4.87% | +11.05 |

## Top Losers (1 Day)

| Symbol | Price | % Change | $ Change |
|--------|-------|----------|----------|
| AAPL   | $189.30 | -2.15% | -4.17 |
| MSFT   | $378.90 | -1.98% | -7.62 |
```

## MCP Tools Required

- `Robinhood:get_accounts` — Fetch all linked Robinhood accounts
- `Robinhood:get_equity_positions` — Fetch current stock holdings per account
- `Robinhood:get_crypto_positions` — Fetch current crypto holdings per account
- `Robinhood:get_equity_quotes` — Fetch current stock quotes for held symbols
- `Robinhood:get_crypto_quotes` — Fetch current crypto prices for held symbols
- `Robinhood:get_equity_historicals` — Fetch historical price data for % change calculation (for week/month ranges)
- `Robinhood:get_crypto_historicals` — Fetch historical crypto data (if available)

## Next Steps

If the user wants to:
- **Analyze a specific holding**: Pull technical indicators (RSI, MACD, Ichimoku, etc.) for positions
- **Rebalance**: Review allocation and compare to benchmark allocations
- **Set alerts**: Create price or indicator alerts for top gainers/losers in portfolio
- **Track P&L**: Fetch realized gains/losses and tax-lot details
- **Compare performance**: Run portfolio performance vs market index (S&P 500, etc.)
- **Deep dive on a losing position**: Check news, technicals, or fundamentals for underperforming holdings
