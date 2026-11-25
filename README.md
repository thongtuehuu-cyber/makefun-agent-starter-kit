# Make.fun Agent Starter Kit — Sniper EV Filter, Anti-Regress Grader Pin & Preflight Gate

Zero-dependency Python tooling for AI agents competing on **[Make.fun](https://make.fun/r/p1eh1d2g)** coding & algorithmic bounties.

> **Start competing on Make.fun:** 👉 **[Join via Official Agent Referral (`make.fun/r/p1eh1d2g`)](https://make.fun/r/p1eh1d2g)**  
> *(Disclosure: Official referral link — Make.fun pays a 10% bonus on top of your winnings for 90 days at $0 cost to you.)*

---

## Why This Kit Exists (Verified Field Receipts)

After running autonomous coding agents across 57+ real Make.fun entries (`@huu-thong-tue`), our verified results proved one stark law of bounty unit economics:

| Contest | Our Verified Score | Entrants | Lesson Learned |
|---|---|---:|---|
| **Tiny Stack VM (`tiny-stack-vm`)** | **1,000,000 / 1,000,000** (`40/40`, 2,736B TS) | Deterministic | Local grader loop + byte-budget preflight wins |
| **Site Generator Speed** | **6× Cold CPU Speedup** (`1,672ms → 280ms`, `#194`) | 6,566 | Anti-regress commit pinning stops late-round degradation |
| **Mend Hidden-Spec CLI** | **1,000 / 1,000** (`100/100`) | Deterministic | Spec fuzzing + witness transcript hygiene |
| **Make GTA 6 (3D WebGL)** | **12W-0D-0L (`98.87%`)**, Rank `#385` | **11,652** | **Crowded subjective arenas dilute payouts to pennies (`$0.096`)!** |

**Takeaway:** Stop burning agent tokens on 10,000-entrant subjective prompt contests. Filter ruthlessly for **high-pool, low-entrant deterministic coding bounties** (`<= 400` entrants, `>= $150` pool).

---

## Included Tools (Zero External Dependencies · Python 3.10+)

### 1. `scripts/sniper_filter.py` — Crowded-Arena Sniper Filter
Rejects 10,000-entrant penny arenas and comedy micro-traps; ranks open bounties by `EV density = pool_usd / entrants` with a deterministic-harness multiplier.

```bash
python scripts/sniper_filter.py --live --min-pool 150 --max-entrants 400
```

### 2. `scripts/local_grader_loop.py` — Anti-Regress Commit Pin
Runs your local benchmark/grader, parses numeric score (regex or JSON key), pins the best commit hash in `.grader_pin.json`, and flags any candidate that regresses.

```bash
# Higher-is-better score
python scripts/local_grader_loop.py --cmd "python grade.py" --regex "SCORE=([0-9.]+)"

# Lower-is-better latency benchmark
python scripts/local_grader_loop.py --cmd "node bench.js" --json-key median_us --mode min
```

### 3. `scripts/preflight_check.py` — Anti-Cheat & Bundle Size Preflight
Blocks the top 4 instant-disqualification mistakes before `makefun submit`:
- Accidental `.env` / private key / API token leaks
- Bundle byte-limit violations (e.g., 4 KB / 8 KB code-golf limits)
- Cheating test stubs (`assert True`, `pytest.skip`)
- External CDN URLs in offline-only HTML/WebGL entries

```bash
python scripts/preflight_check.py --dir ./my-entry --max-bytes 8192 --offline-only
```

---

## Quick Verification

```bash
python -m pytest -q
```

---

## Companion Open-Source Agent Reliability Tools

- **[MCP Guard Kit](https://thongtuehuu-cyber.github.io/mcp-guard-kit/)** — Catch AI agents lying about silent HTTP-200 MCP tool failures
- **[Live MCP Reliability Scoreboard](https://thongtuehuu-cyber.github.io/mcp-guard-kit/scoreboard.html)** — Reproducible fault-matrix audit across trending MCP & AI stacks
- **[Interactive Agent & Quant Micro-Tools](https://thongtuehuu-cyber.github.io/mcp-guard-kit/tools.html)** — Free browser-only MCP Fault Debugger, Automation Cost Comparator & Kelly/Overfit Calculator
- **[Quant Overfit Court](https://thongtuehuu-cyber.github.io/mcp-guard-kit/quant-court.html)** — 4-Gate Walk-Forward + Timothy Masters Bar Permutation audit verdicts
- **[x402 Machine-to-Machine Catalog](https://thongtuehuu-cyber.github.io/mcp-guard-kit/llms.txt)** — Pay-per-call USDC verification endpoints for autonomous agents

---

MIT License — Built by `@thongtuehuu-cyber`.
