# claude-skills

Custom [Claude skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview), packaged as Claude Code plugins.

## Skills

### [robinhood-gainers-losers](robinhood-gainers-losers/skills/robinhood-gainers-losers/SKILL.md)

Shows which of your own Robinhood holdings are up or down over **1 day, 1 week or 1 month**, with separate tables per account: symbol, quantity, price, % change, $ change and position value.

- **Read-only:** it never places, changes or cancels orders.
- **Needs:** the Robinhood connector (MCP) enabled in Claude.
- **Try:** "How's my portfolio doing today?", "Top 5 losers this month", "Break down my gains by account".
- **Limitation:** Robinhood's tools don't provide crypto price history, so crypto week/month changes show as N/A.

Claude fetches the data; [`scripts/compute_gainers_losers.py`](robinhood-gainers-losers/skills/robinhood-gainers-losers/scripts/compute_gainers_losers.py) does the math and formatting so the numbers are consistent.

## Layout

```
robinhood-gainers-losers/
├── .claude-plugin/plugin.json          # plugin manifest
└── skills/robinhood-gainers-losers/
    ├── SKILL.md                        # instructions Claude follows
    ├── references/implementation.md    # tool parameters, formulas, edge cases
    ├── scripts/compute_gainers_losers.py
    ├── scripts/test_compute_gainers_losers.py
    └── test-cases.json                 # prompts + expected behavior for evals
```

## Installing

- **Claude Code:** copy `robinhood-gainers-losers/skills/robinhood-gainers-losers` into `~/.claude/skills/` (all projects) or `.claude/skills/` in a project.
- **Claude apps:** zip the `robinhood-gainers-losers/skills/robinhood-gainers-losers` folder and upload it under Settings → Capabilities → Skills.

## Development

```bash
python3 -m pytest robinhood-gainers-losers/skills/robinhood-gainers-losers/scripts/
```

The script uses only the Python standard library (3.9+); the tests need `pytest`.
