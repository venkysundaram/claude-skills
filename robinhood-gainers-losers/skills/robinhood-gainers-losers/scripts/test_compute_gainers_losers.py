"""Unit tests for compute_gainers_losers.py. Run: python3 -m pytest scripts/"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import compute_gainers_losers as cgl  # noqa: E402

SCRIPT = Path(__file__).parent / "compute_gainers_losers.py"
TODAY = date(2026, 9, 25)  # a Friday


def holding(symbol, price, ref, qty=10, kind="equity", **extra):
    return {"symbol": symbol, "type": kind, "quantity": qty, "price": price, "reference_price": ref, **extra}


def run(accounts, **opts):
    return cgl.compute({"accounts": accounts, **opts}, today=TODAY)


def test_math():
    h = cgl.evaluate_holding(holding("NVDA", 110.0, 100.0, qty=5), "1day")
    assert h["pct_change"] == pytest.approx(10.0)
    assert h["dollar_change"] == pytest.approx(10.0)
    assert h["position_change"] == pytest.approx(50.0)
    assert h["position_value"] == pytest.approx(550.0)


def test_sorting_and_flat():
    acct = {"name": "Main", "holdings": [
        holding("A", 101, 100), holding("B", 105, 100), holding("C", 97, 100),
        holding("D", 90, 100), holding("E", 100, 100),
    ]}
    a = run([acct])["accounts"][0]
    assert [h["symbol"] for h in a["gainers"]] == ["B", "A"]
    assert [h["symbol"] for h in a["losers"]] == ["D", "C"]
    assert [h["symbol"] for h in a["unchanged"]] == ["E"]


def test_limit_keeps_totals():
    acct = {"holdings": [holding(f"S{i}", 100 + i, 100) for i in range(1, 6)]}
    a = run([acct], limit=2)["accounts"][0]
    assert len(a["gainers"]) == 2 and a["gainers_total"] == 5
    assert "top 2 of 5" in cgl.format_markdown(run([acct], limit=2))


def test_missing_price_and_reference_are_reported():
    acct = {"holdings": [holding("X", None, 100), holding("Y", 50, None)]}
    a = run([acct])["accounts"][0]
    reasons = {h["symbol"]: h["unavailable"] for h in a["unavailable"]}
    assert reasons == {"X": "no current price", "Y": "no reference price"}
    assert a["total_value"] == pytest.approx(500.0)  # Y still counts toward value


def test_crypto_week_is_na_but_valued():
    acct = {"holdings": [holding("BTCUSD", 60000, None, qty=0.5, kind="crypto")]}
    a = run([acct], time_range="1week")["accounts"][0]
    assert a["unavailable"][0]["unavailable"] == "no crypto price history for this range"
    assert a["total_value"] == pytest.approx(30000.0)


def test_asset_class_filter():
    acct = {"holdings": [holding("AAPL", 101, 100), holding("ETHUSD", 2100, 2000, kind="crypto")]}
    assert [h["symbol"] for h in run([acct], asset_class="crypto")["accounts"][0]["gainers"]] == ["ETHUSD"]
    assert [h["symbol"] for h in run([acct], asset_class="stocks")["accounts"][0]["gainers"]] == ["AAPL"]


def test_reference_from_bars_uses_last_close_before_period():
    # 1week from Fri 2026-09-25 starts Fri 2026-09-18; reference is Thu 09-17 close
    bars = [{"date": "2026-09-16", "close": 90}, {"begins_at": "2026-09-17T13:30:00Z", "close": 95},
            {"date": "2026-09-18", "close": 99}, {"date": "2026-09-24", "close": 104}]
    h = cgl.evaluate_holding(holding("VOO", 104.5, None, daily_bars=bars), "1week", today=TODAY)
    assert h["reference_price"] == 95
    assert h["pct_change"] == pytest.approx(10.0)


def test_interpolated_bars_are_ignored():
    bars = [{"date": "2026-09-16", "close": 90}, {"date": "2026-09-17", "close": 95, "interpolated": True}]
    assert cgl.reference_from_bars(bars, date(2026, 9, 18)) == 90


def test_historicals_start_time_is_utc_before_period():
    assert cgl.historicals_start_time("1week", today=TODAY) == "2026-09-11T04:00:00Z"


def test_markdown_single_vs_multi_account():
    one = cgl.format_markdown(run([{"name": "Main", "holdings": [holding("A", 101, 100)]}]))
    assert "My Holdings — Gainers" in one and "### Account:" not in one

    two = cgl.format_markdown(run([
        {"name": "Main", "account_number": "5QR12345", "holdings": [holding("A", 101, 100)]},
        {"name": "Roth IRA", "holdings": [holding("B", 99, 100)]},
    ]))
    assert "### Account: Main (…2345)" in two and "### Account: Roth IRA" in two
    assert "5QR12345" not in two


def test_small_crypto_prices_keep_precision():
    out = cgl.format_markdown(run([{"holdings": [holding("DOGEUSD", 0.1234, 0.12, qty=1000, kind="crypto")]}]))
    assert "$0.1234" in out and "+$0.0034" in out


def test_stock_cents_use_two_decimals():
    out = cgl.format_markdown(run([{"holdings": [holding("BND", 73.10, 73.25, qty=50)]}]))
    assert "| -$0.15 |" in out


def test_cli_end_to_end(tmp_path):
    data = tmp_path / "in.json"
    data.write_text(json.dumps({"accounts": [{"holdings": [holding("A", 101, 100)]}]}))
    out = subprocess.run([sys.executable, str(SCRIPT), "--input", str(data)],
                         capture_output=True, text=True, check=True).stdout
    assert "| A | 10 | $101.00 | +1.00% |" in out
    assert "ET*" in out or "EDT*" in out or "EST*" in out
