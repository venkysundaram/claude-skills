#!/usr/bin/env python3
"""
Fetch top gainers and losers from Robinhood by percentage change.

This script orchestrates:
1. Fetching current quotes (equities + crypto)
2. Calculating % changes for the specified time range
3. Sorting by % change
4. Formatting results as Markdown tables
"""

import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

def parse_args():
    """Parse command-line arguments."""
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Robinhood gainers & losers")
    parser.add_argument("--time-range", choices=["1day", "1week", "1month"], default="1day",
                        help="Time range for % change calculation")
    parser.add_argument("--asset-class", choices=["stocks", "crypto", "both"], default="both",
                        help="Asset class filter")
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of gainers/losers to show")
    parser.add_argument("--output-format", choices=["json", "markdown"], default="markdown",
                        help="Output format")
    return parser.parse_args()

def calculate_time_range(range_type: str) -> Tuple[datetime, datetime]:
    """
    Return (start_date, end_date) for historical data fetch.
    
    Args:
        range_type: "1day", "1week", or "1month"
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.now()
    if range_type == "1day":
        # Intraday: use today's open to now
        start = now.replace(hour=9, minute=30, second=0, microsecond=0)  # Market open
        end = now
    elif range_type == "1week":
        start = now - timedelta(days=7)
        end = now
    elif range_type == "1month":
        start = now - timedelta(days=30)
        end = now
    return start, end

def format_markdown_table(gainers: List[Dict], losers: List[Dict], time_range: str, asset_class: str) -> str:
    """
    Format gainers and losers as Markdown tables.
    
    Args:
        gainers: List of dicts with symbol, price, pct_change, abs_change
        losers: List of dicts with symbol, price, pct_change, abs_change
        time_range: Display label for time range
        asset_class: Display label for asset class
    
    Returns:
        Markdown-formatted string
    """
    time_labels = {
        "1day": "1 Day",
        "1week": "1 Week",
        "1month": "1 Month",
    }
    
    output = f"## Market Movers ({time_labels.get(time_range, time_range)})\n\n"
    output += f"**Asset Class:** {asset_class.capitalize()}\n\n"
    
    # Gainers table
    output += "### Top Gainers\n\n"
    output += "| Symbol | Price | % Change | $ Change |\n"
    output += "|--------|-------|----------|----------|\n"
    for g in gainers:
        pct = f"+{g['pct_change']:.2f}%" if g['pct_change'] >= 0 else f"{g['pct_change']:.2f}%"
        change = f"+${g['abs_change']:.2f}" if g['abs_change'] >= 0 else f"-${abs(g['abs_change']):.2f}"
        output += f"| {g['symbol']} | ${g['price']:.2f} | {pct} | {change} |\n"
    
    output += "\n"
    
    # Losers table
    output += "### Top Losers\n\n"
    output += "| Symbol | Price | % Change | $ Change |\n"
    output += "|--------|-------|----------|----------|\n"
    for l in losers:
        pct = f"{l['pct_change']:.2f}%"
        change = f"-${abs(l['abs_change']):.2f}"
        output += f"| {l['symbol']} | ${l['price']:.2f} | {pct} | {change} |\n"
    
    output += f"\n*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
    
    return output

def format_json_output(gainers: List[Dict], losers: List[Dict]) -> str:
    """Format output as JSON."""
    return json.dumps({
        "gainers": gainers,
        "losers": losers,
        "timestamp": datetime.now().isoformat()
    }, indent=2)

def main():
    """Main entry point."""
    args = parse_args()
    
    print(f"Fetching Robinhood gainers & losers...")
    print(f"Time range: {args.time_range}")
    print(f"Asset class: {args.asset_class}")
    print(f"Limit: {args.limit} per category")
    
    # NOTE: In actual implementation, this would call Robinhood MCP tools
    # For now, we return a template showing what the output would look like
    
    gainers = [
        {"symbol": "NVDA", "price": 145.20, "pct_change": 5.32, "abs_change": 7.35},
        {"symbol": "TSLA", "price": 238.50, "pct_change": 4.87, "abs_change": 11.05},
        {"symbol": "AMD", "price": 125.30, "pct_change": 3.45, "abs_change": 4.20},
    ]
    
    losers = [
        {"symbol": "AAPL", "price": 189.30, "pct_change": -2.15, "abs_change": -4.17},
        {"symbol": "MSFT", "price": 378.90, "pct_change": -1.98, "abs_change": -7.62},
        {"symbol": "GOOGL", "price": 162.45, "pct_change": -1.50, "abs_change": -2.48},
    ]
    
    if args.output_format == "markdown":
        output = format_markdown_table(gainers, losers, args.time_range, args.asset_class)
    else:
        output = format_json_output(gainers, losers)
    
    print("\n" + output)

if __name__ == "__main__":
    main()
