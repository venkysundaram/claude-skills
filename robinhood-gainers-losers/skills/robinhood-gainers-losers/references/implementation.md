# Implementation Reference: Robinhood Portfolio Gainers & Losers

Detail behind the workflow in `SKILL.md`. Tool names are the Robinhood MCP connector's; exact response field names can differ between connector versions, so map from what the response actually contains.

## Tool Calls

### `get_accounts`
No parameters. For each account, record:
- a display name (account type / nickname)
- `account_number`: alphanumeric, used for equity positions
- `rhs_account_number`: numeric, used for crypto positions and crypto quotes
- ignore `rhc_account_number` (the linked crypto account). Passing it to `get_crypto_positions` returns nothing.

### `get_equity_positions`
| Param | Notes |
|---|---|
| `account_number` | required, from `get_accounts` |
| `cursor` | omit on the first call; pass the previous response's `next` to get the next page |

Returns symbol, quantity, average cost per position.

### `get_crypto_positions`
| Param | Notes |
|---|---|
| `rhs_account_number` | required, numeric |
| `cursor` | same paging as above |

Returns asset, quantity and cost basis. Build the quote symbol as `<ASSET>-USD`.

### `get_equity_quotes`
| Param | Notes |
|---|---|
| `symbols` | list; **≤ 20 per call**. Above 20, quotes still come back, but `closes` is omitted and `closes_error` is set |

Use the last trade price as `price` and the official last-completed-session close as `reference_price` for `1day`.

### `get_crypto_quotes`
| Param | Notes |
|---|---|
| `symbols` | e.g. `["BTC-USD", "ETH-USD"]`; the response symbol comes back unhyphenated (`BTCUSD`) |
| `rhs_account_number` | optional; prices on that account's routing |
| `timezone` | optional IANA name; pass **only** if the user's timezone is known. Default anchors the previous close to midnight ET |

Use the mark price as `price` and the previous close (`open_price`) as `reference_price` for `1day`. Crypto trades 24/7, so "1 day" means since the previous midnight close.

### `get_equity_historicals` (week / month only)
| Param | Notes |
|---|---|
| `symbols` | **≤ 10 per call** |
| `start_time` | required, RFC3339 UTC. Get it from `compute_gainers_losers.py --period-start 1week` or `1month` |
| `interval` | `"day"` |
| `bounds` | leave default (`regular`) |
| `end_time` | omit (defaults to now) |

Bars flagged `interpolated: true` are gap fillers. Pass the flag through and the script ignores them.

There is **no crypto historicals tool**, so crypto week/month changes are N/A.

## Period Definitions

| Range | Reference price |
|---|---|
| `1day` | stocks: last completed regular-session close · crypto: previous close from the quote |
| `1week` | close of the last trading day before *today − 7 days* (ET) |
| `1month` | close of the last trading day before *today − 30 days* (ET) |

`--period-start` begins a week earlier than the period itself, so that close is included even across weekends and holidays. The script picks it from `daily_bars`.

## Script Input

```json
{
  "time_range": "1week",
  "asset_class": "both",
  "limit": 15,
  "accounts": [
    {
      "name": "Individual",
      "account_number": "5QR12345",
      "holdings": [
        {"symbol": "NVDA", "type": "equity", "quantity": 10, "price": 182.40,
         "daily_bars": [{"date": "2026-09-17", "close": 175.10},
                        {"date": "2026-09-18", "close": 176.95}]},
        {"symbol": "BTCUSD", "type": "crypto", "quantity": 0.05, "price": 112500.00}
      ]
    },
    {
      "name": "Roth IRA",
      "account_number": "7AB67890",
      "holdings": [
        {"symbol": "VOO", "type": "equity", "quantity": 15, "price": 601.20, "reference_price": 598.00}
      ]
    }
  ]
}
```

- Give either `reference_price` or `daily_bars` (week/month). For `1day`, always use `reference_price`.
- A holding missing `price` or a usable reference is reported under "Not included" with a reason. Holdings missing only a reference still count toward the account's total value.
- The same symbol held in two accounts appears once in each account.

Run it:

```bash
python3 scripts/compute_gainers_losers.py --input /tmp/rh_portfolio.json            # Markdown
python3 scripts/compute_gainers_losers.py --input /tmp/rh_portfolio.json --format json
```

## Calculations (done by the script)

```
pct_change      = (price − reference_price) / reference_price × 100
dollar_change   = price − reference_price            (per share / per coin)
position_change = dollar_change × quantity
position_value  = price × quantity
```

- Gainers: `pct_change > 0`, sorted descending.
- Losers: `pct_change < 0`, sorted ascending (worst first).
- Exactly 0: listed as "Unchanged".
- `limit` applies per category, per account; the heading shows "top N of M" when rows are cut.

## Edge Cases

| Case | Handling |
|---|---|
| No accounts / no positions | Say so plainly; don't render empty tables for every account |
| More than 20 stock symbols | Batch quote calls by 20 and merge results |
| More than 10 symbols for history | Batch historicals calls by 10 |
| Quote missing for a symbol | Omit `price`; the script lists it as unavailable |
| Crypto + week/month | Omit `reference_price`; shown as N/A, value still counted |
| Recent purchase within the period | Still uses the market reference price. This is market performance, not the user's own P&L; point to `get_realized_pnl` / cost basis if they want that |
| Options positions | Out of scope; mention if the user asks |

## Example

```
User: "How did my holdings do this week?"

1. time_range=1week, asset_class=both, all accounts
2. get_accounts → Individual (5QR12345 / rhs 111), Roth IRA (7AB67890 / rhs 222)
3. get_equity_positions + get_crypto_positions for each (following cursors)
4. get_equity_quotes (≤20/call) + get_crypto_quotes for held symbols
5. --period-start 1week → start_time; get_equity_historicals (≤10/call, interval=day)
6. Write JSON → run the script → show tables
7. "NVDA led your Individual account at +4.2%; BTC is not included for weekly
   ranges because Robinhood doesn't provide crypto history."
```
