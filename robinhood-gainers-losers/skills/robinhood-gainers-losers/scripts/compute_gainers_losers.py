#!/usr/bin/env python3
"""
Compute and format per-account gainers & losers for a Robinhood portfolio.

This script does NOT call Robinhood. Claude fetches accounts, positions,
quotes and historicals with the Robinhood MCP tools, writes them to a JSON
file in the shape below, and runs this script to do the math and render the
tables, so the numbers are deterministic and testable.

Input JSON:

{
  "time_range": "1day" | "1week" | "1month",       # default "1day"
  "asset_class": "stocks" | "crypto" | "both",     # default "both"
  "limit": 15,                                     # per category, per account
  "accounts": [
    {
      "name": "Individual",
      "account_number": "5QR12345",                # optional, shown masked
      "holdings": [
        {
          "symbol": "NVDA",
          "type": "equity" | "crypto",
          "quantity": 10,
          "price": 145.20,                          # current price
          "reference_price": 137.85,               # price to compare against
          "daily_bars": [                           # alternative to reference_price
            {"date": "2026-09-18", "close": 140.10}  # (week/month ranges)
          ]
        }
      ]
    }
  ]
}

reference_price is the previous close for "1day", or the close of the last
trading day before the period start for "1week"/"1month". If it is omitted
and daily_bars are given, the script picks that close itself. Holdings with
no usable price or reference are listed as unavailable instead of dropped.

Usage:
  compute_gainers_losers.py --input data.json [--format markdown|json]
  compute_gainers_losers.py --period-start 1week   # prints start_time for historicals
"""

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

TIME_LABELS = {"1day": "1 Day", "1week": "1 Week", "1month": "1 Month"}
PERIOD_DAYS = {"1week": 7, "1month": 30}
DEFAULT_LIMIT = 15


def period_start_date(time_range: str, today: Optional[date] = None) -> date:
    """First calendar day of the period, in US Eastern time."""
    today = today or datetime.now(ET).date()
    return today - timedelta(days=PERIOD_DAYS[time_range])


def historicals_start_time(time_range: str, today: Optional[date] = None) -> str:
    """
    RFC3339 UTC start_time for get_equity_historicals.

    Starts a week before the period so the last close *before* the period is
    included even across weekends and holidays.
    """
    start = period_start_date(time_range, today) - timedelta(days=7)
    start_et = datetime.combine(start, time(0, 0), tzinfo=ET)
    return start_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reference_from_bars(bars: List[Dict], start: date) -> Optional[float]:
    """Close of the last daily bar dated before the period start."""
    before = [b for b in bars
              if b.get("close") is not None and not b.get("interpolated") and _bar_date(b) < start]
    if not before:
        return None
    return float(max(before, key=_bar_date)["close"])


def _bar_date(bar: Dict) -> date:
    raw = bar.get("date") or bar.get("begins_at")
    return date.fromisoformat(str(raw)[:10])


def evaluate_holding(holding: Dict, time_range: str, today: Optional[date] = None) -> Dict:
    """Return the holding with pct_change, dollar_change, position_value, or an unavailable reason."""
    result = {
        "symbol": holding["symbol"],
        "type": holding.get("type", "equity"),
        "quantity": float(holding.get("quantity") or 0),
        "price": holding.get("price"),
    }

    if result["price"] is None:
        result["unavailable"] = "no current price"
        return result
    price = float(result["price"])
    result["price"] = price
    result["position_value"] = price * result["quantity"]

    if result["type"] == "crypto" and time_range != "1day" and holding.get("reference_price") is None:
        result["unavailable"] = "no crypto price history for this range"
        return result

    reference = holding.get("reference_price")
    if reference is None and holding.get("daily_bars") and time_range != "1day":
        reference = reference_from_bars(holding["daily_bars"], period_start_date(time_range, today))
    if reference is None or float(reference) == 0:
        result["unavailable"] = "no reference price"
        return result

    reference = float(reference)
    result["reference_price"] = reference
    result["dollar_change"] = price - reference
    result["pct_change"] = (price - reference) / reference * 100
    result["position_change"] = result["dollar_change"] * result["quantity"]
    return result


def summarize_account(account: Dict, time_range: str, asset_class: str,
                      limit: int, today: Optional[date] = None) -> Dict:
    wanted = {"stocks": {"equity"}, "crypto": {"crypto"}, "both": {"equity", "crypto"}}[asset_class]
    holdings = [h for h in account.get("holdings", []) if h.get("type", "equity") in wanted]
    evaluated = [evaluate_holding(h, time_range, today) for h in holdings]

    priced = [h for h in evaluated if "pct_change" in h]
    gainers = sorted((h for h in priced if h["pct_change"] > 0), key=lambda h: h["pct_change"], reverse=True)
    losers = sorted((h for h in priced if h["pct_change"] < 0), key=lambda h: h["pct_change"])

    return {
        "name": account.get("name") or "Account",
        "account_number": account.get("account_number"),
        "gainers": gainers[:limit],
        "losers": losers[:limit],
        "gainers_total": len(gainers),
        "losers_total": len(losers),
        "unchanged": [h for h in priced if h["pct_change"] == 0],
        "unavailable": [h for h in evaluated if "unavailable" in h],
        "total_value": sum(h.get("position_value", 0) for h in evaluated),
        "total_change": sum(h["position_change"] for h in priced),
    }


def compute(data: Dict, today: Optional[date] = None) -> Dict:
    time_range = data.get("time_range", "1day")
    asset_class = data.get("asset_class", "both")
    limit = int(data.get("limit") or DEFAULT_LIMIT)
    if time_range not in TIME_LABELS:
        raise ValueError(f"time_range must be one of {sorted(TIME_LABELS)}")
    return {
        "time_range": time_range,
        "asset_class": asset_class,
        "generated_at": datetime.now(ET).strftime("%Y-%m-%d %H:%M %Z"),
        "accounts": [summarize_account(a, time_range, asset_class, limit, today)
                     for a in data.get("accounts", [])],
    }


def _money(value: float, signed: bool = False, fine: bool = False) -> str:
    """Format dollars; fine=True adds precision for sub-$1 assets."""
    decimals = 4 if fine else 2
    text = f"${abs(value):,.{decimals}f}"
    if value < 0:
        return "-" + text
    return ("+" + text) if signed else text


def _qty(value: float) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")


def _mask(account_number: Optional[str]) -> str:
    return f" (…{account_number[-4:]})" if account_number else ""


def _table(rows: List[Dict]) -> List[str]:
    lines = ["| Symbol | Qty | Price | % Change | $ Change / Share | Position Change | Position Value |",
             "|--------|-----|-------|----------|------------------|-----------------|----------------|"]
    for h in rows:
        fine = h["price"] < 1
        lines.append(
            f"| {h['symbol']} | {_qty(h['quantity'])} | {_money(h['price'], fine=fine)} | {h['pct_change']:+.2f}% "
            f"| {_money(h['dollar_change'], signed=True, fine=fine)} | {_money(h['position_change'], signed=True)} "
            f"| {_money(h['position_value'])} |"
        )
    return lines


def format_markdown(result: Dict) -> str:
    label = TIME_LABELS[result["time_range"]]
    accounts = result["accounts"]
    single = len(accounts) == 1
    out = [f"## My Robinhood Portfolio ({label})", "",
           f"**Asset class:** {result['asset_class'].capitalize()}", ""]

    if not accounts:
        out.append("_No accounts found._")

    for acct in accounts:
        prefix = "My Holdings" if single else "Holdings"
        if not single:
            out += [f"### Account: {acct['name']}{_mask(acct['account_number'])}", ""]
        out += [f"**Total value:** {_money(acct['total_value'])} · "
                f"**{label} change:** {_money(acct['total_change'], signed=True)}", ""]

        for title, rows, total in (("Gainers", acct["gainers"], acct["gainers_total"]),
                                   ("Losers", acct["losers"], acct["losers_total"])):
            shown = f" (top {len(rows)} of {total})" if total > len(rows) else ""
            out += [f"#### {prefix} — {title}{shown}", ""]
            out += (_table(rows) if rows else [f"_No {title.lower()}._"]) + [""]

        if acct["unchanged"]:
            out += ["Unchanged: " + ", ".join(h["symbol"] for h in acct["unchanged"]), ""]
        if acct["unavailable"]:
            out += ["Not included: " + ", ".join(f"{h['symbol']} ({h['unavailable']})"
                                                 for h in acct["unavailable"]), ""]

    out.append(f"*Generated {result['generated_at']}*")
    return "\n".join(out)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Compute Robinhood portfolio gainers & losers")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Path to input JSON, or '-' for stdin")
    group.add_argument("--period-start", choices=["1week", "1month"],
                       help="Print the start_time to pass to get_equity_historicals")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.period_start:
        print(historicals_start_time(args.period_start))
        return
    with (sys.stdin if args.input == "-" else open(args.input)) as f:
        data = json.load(f)
    result = compute(data)
    print(format_markdown(result) if args.format == "markdown" else json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
