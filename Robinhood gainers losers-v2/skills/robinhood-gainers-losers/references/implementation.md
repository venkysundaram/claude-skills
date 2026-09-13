# Implementation Reference: Robinhood Portfolio Gainers & Losers

## How Claude Should Execute This Skill

### Step 1: Extract Intent & Parameters

When a user triggers this skill, extract:
- **Time range**: "1 day" (default), "1 week", or "1 month"
- **Asset class**: "stocks", "crypto", or "both" (default)
- **Account filter**: Optional — "all accounts" (default) or specific account name

### Step 2: Fetch All Accounts & Holdings

Get the user's accounts and their holdings:

```javascript
// Get all linked accounts
const accountsResponse = await robinhoodTool.get_accounts();
// Returns: [{ account_id: "...", account_number: "...", account_type: "cash", display_name: "..." }, ...]

// For each account, fetch holdings
for (const account of accountsResponse) {
  const equityPositions = await robinhoodTool.get_equity_positions({ 
    account: account.account_id 
  });
  
  const cryptoPositions = await robinhoodTool.get_crypto_positions({ 
    account: account.account_id 
  });
  
  // Collect all symbols from positions
  const symbols = [
    ...equityPositions.map(p => p.symbol),
    ...cryptoPositions.map(p => p.currency_pair)
  ];
}
```

### Step 3: Fetch Current Quotes for Holdings

Query current prices for all held symbols:

```javascript
// Get quotes for stocks you hold
const stockQuotes = await robinhoodTool.get_equity_quotes({
  symbols: [symbols from equity positions], // e.g., ["NVDA", "TSLA", "FSLR"]
});

// Get quotes for crypto you hold
const cryptoQuotes = await robinhoodTool.get_crypto_quotes({
  currency_pairs: [pairs from crypto positions], // e.g., ["BTCUSD", "ETHUSD"]
});
```

### Step 4: Calculate % Changes by Time Range

#### For 1 Day (Intraday)
The quote data includes `previous_close`, so:
```javascript
pctChange = ((currentPrice - previousClose) / previousClose) × 100
dollarChange = currentPrice - previousClose
```

#### For 1 Week or 1 Month
Fetch historical data for the start of the period:

```javascript
// Example: Get historical data for 1 month
const historicals = await robinhoodTool.get_equity_historicals({
  symbol: "NVDA",
  interval: "day",
  span: "month",
  bounds: "trading"
});

// Extract first day's open and current price
const startPrice = historicals[0].open; // Price at start of period
const endPrice = currentQuote.last_price; // Current price
const pctChange = ((endPrice - startPrice) / startPrice) × 100;
```

### Step 5: Match Holdings with Quotes & Calculate Position P&L

```python
# Pseudo-code: per account
for account in all_accounts:
  holdings = equity_positions[account] + crypto_positions[account]
  
  for holding in holdings:
    current_price = get_quote(holding.symbol)
    pct_change = calc_pct_change(holding, current_price)
    dollar_change = calc_dollar_change(holding, current_price)
    position_value = current_price * holding.quantity
    holding['perf'] = (pct_change, dollar_change, position_value)
  
  gainers = [h for h in holdings if h['perf'][0] > 0]
  gainers.sort(key=lambda x: x['perf'][0], reverse=True)
  
  losers = [h for h in holdings if h['perf'][0] < 0]
  losers.sort(key=lambda x: x['perf'][0])  # Ascending (most negative first)
```

### Step 6: Format and Display by Account

Use Markdown tables, one account per section:

```markdown
## My Robinhood Portfolio (1 Day)

### Account: Main Brokerage

#### Holdings - Gainers

| Symbol | Qty | Price | % Change | $ Change | Position Value |
|--------|-----|-------|----------|----------|-----------------|
| FSLR   | 50  | $87.50 | +2.15% | +$1.85 | $4,375.00 |
| NVDA   | 10  | $145.20 | +1.32% | +$1.89 | $1,452.00 |

#### Holdings - Losers

| Symbol | Qty | Price | % Change | $ Change | Position Value |
|--------|-----|-------|----------|----------|-----------------|
| AAPL   | 25  | $189.30 | -0.85% | -$1.64 | $4,732.50 |

### Account: Roth IRA

#### Holdings - Gainers

| Symbol | Qty | Price | % Change | $ Change | Position Value |
|--------|-----|-------|----------|----------|-----------------|
| VOO    | 15  | $482.10 | +0.42% | +$2.03 | $7,231.50 |

#### Holdings - Losers

| Symbol | Qty | Price | % Change | $ Change | Position Value |
|--------|-----|-------|----------|----------|-----------------|
| BND    | 50  | $78.20 | -0.12% | -$0.09 | $3,910.00 |
```

## MCP Tool Reference

### `Robinhood:get_equity_quotes`

Fetch real-time or near-real-time stock quotes.

**Parameters:**
- `symbols` (list): List of stock symbols (e.g., ["NVDA", "TSLA"])

**Returns:**
```json
{
  "symbol": "NVDA",
  "last_price": 145.20,
  "previous_close": 137.85,
  "bid": 145.15,
  "ask": 145.25,
  "volume": 52_000_000
}
```

### `Robinhood:get_crypto_quotes`

Fetch current cryptocurrency prices.

**Parameters:**
- `currency_pairs` (list): List of crypto pairs (e.g., ["BTCUSD", "ETHUSD"])

**Returns:**
```json
{
  "currency_pair": "BTCUSD",
  "mark_price": 45_320.50,
  "bid": 45_315.00,
  "ask": 45_326.00,
  "high_price": 46_200.00,
  "low_price": 44_850.00
}
```

### `Robinhood:get_equity_historicals`

Fetch historical OHLC data for % change calculations over longer periods.

**Parameters:**
- `symbol` (str): Stock symbol
- `interval` (str): "day", "week", "month"
- `span` (str): "day", "week", "month", "3month", "year", "5year"
- `bounds` (str): "trading", "24_7", "extended"

**Returns:**
```json
[
  {
    "open": 140.50,
    "high": 146.20,
    "low": 138.90,
    "close": 145.20,
    "volume": 45_000_000,
    "begins_at": "2026-09-12T00:00:00Z"
  }
]
```

## Handling Edge Cases

### No Data Available
If a symbol has no historical data or quotes are unavailable, skip it and note in the output.

### Market Hours vs. Extended Hours
For "1 day" calculations, decide whether to use:
- **Trading hours only** (9:30 AM – 4:00 PM ET)
- **Extended hours** (4:00 AM – 8:00 PM ET)

Default to trading hours; offer extended if user asks.

### Sparse Data
If only a few instruments are actively traded in the requested time range, show what's available and note limitations.

## Performance Notes

- **Batch fetches**: If fetching 100+ symbols, batch requests to avoid rate limiting.
- **Caching**: Consider caching recent quote data locally for 5-10 minutes to avoid redundant API calls.
- **Crypto sampling**: Crypto markets trade 24/7, so "1 day" for crypto means the last 24 hours, not intraday from market open.

## Example Workflow

```
User: "Show me today's top gainers on Robinhood"

1. Extract: time_range="1day", asset_class="both", limit=10
2. Fetch: get_equity_quotes() for major symbols
3. Calculate: % change from previous_close
4. Sort: Group gainers/losers, sort by % change
5. Format: Render Markdown table
6. Display: Show top 10 gainers and top 10 losers
```
