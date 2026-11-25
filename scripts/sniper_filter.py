"""Sniper-Only Make.fun Bounty Filter.

Filters out crowded subjective arenas (e.g., 10,000+ entrants paying pennies)
and ranks deterministic coding/algorithm bounties by pool-per-entrant EV density.

Usage:
    python scripts/sniper_filter.py --live --min-pool 150 --max-entrants 400
    python scripts/sniper_filter.py --input sample_bounties.json --max-entrants 400
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SUBJECTIVE_NOISE_RE = re.compile(
    r"\b(one[- ]line|pickup[- ]line|office[- ]joke|comedy|roast|poem|haiku|meme|coffee[- ]or[- ]tea|dumbest)\b",
    re.IGNORECASE,
)
DETERMINISTIC_HINT_RE = re.compile(
    r"\b(cli|compiler|vm|parser|speed|benchmark|algorithm|chess|solver|test|pytest|rust|python|typescript|sql|regex|wasm|compression)\b",
    re.IGNORECASE,
)


@dataclass
class RankedBounty:
    slug: str
    title: str
    pool_usd: float
    submission_count: int
    harness_kind: str
    ev_density_usd: float
    sniper_score: float
    deterministic: bool
    url: str


def evaluate_bounty(
    item: dict[str, Any],
    *,
    min_pool_usd: float = 150.0,
    max_entrants: int = 400,
    allow_subjective: bool = False,
) -> tuple[bool, str, RankedBounty | None]:
    slug = str(item.get("slug") or item.get("id") or "").strip()
    title = str(item.get("title") or item.get("name") or slug).strip()
    desc = str(item.get("description") or item.get("summary") or "")
    pool = float(item.get("prize_usd") or item.get("bounty_usd") or item.get("pool_usd") or 0.0)
    subs = int(item.get("submission_count") or item.get("entrants") or item.get("entries_count") or 0)
    harness = str(item.get("harness_kind") or item.get("harness") or "").strip().lower()
    url = str(item.get("url") or (f"https://make.fun/bounties/{slug}" if slug else "https://make.fun/r/p1eh1d2g"))

    if not slug:
        return False, "missing_slug", None
    if pool < min_pool_usd:
        return False, f"pool_below_min (${pool:g} < ${min_pool_usd:g})", None
    if max_entrants > 0 and subs > max_entrants:
        return False, f"crowded_arena ({subs:,} entrants > {max_entrants:,} cap)", None

    text_blob = f"{slug} {title} {desc}"
    if not allow_subjective and SUBJECTIVE_NOISE_RE.search(text_blob):
        return False, "subjective_comedy_trap", None

    deterministic = bool(
        harness in {"command", "code", "docker", "deterministic", "grader"}
        or DETERMINISTIC_HINT_RE.search(text_blob)
    )
    ev_density = round(pool / max(1, subs), 4)
    det_mult = 1.65 if deterministic else 0.75
    crowd_decay = 1.0 / (1.0 + (subs / 80.0))
    sniper_score = round(pool * det_mult * crowd_decay, 2)

    return (
        True,
        "accepted",
        RankedBounty(
            slug=slug,
            title=title,
            pool_usd=round(pool, 2),
            submission_count=subs,
            harness_kind=harness or ("deterministic" if deterministic else "unknown"),
            ev_density_usd=ev_density,
            sniper_score=sniper_score,
            deterministic=deterministic,
            url=url,
        ),
    )


def filter_and_rank(
    items: list[dict[str, Any]],
    *,
    min_pool_usd: float = 150.0,
    max_entrants: int = 400,
    allow_subjective: bool = False,
) -> dict[str, Any]:
    accepted: list[RankedBounty] = []
    skipped: list[dict[str, Any]] = []
    for raw in items:
        ok, reason, ranked = evaluate_bounty(
            raw,
            min_pool_usd=min_pool_usd,
            max_entrants=max_entrants,
            allow_subjective=allow_subjective,
        )
        if ok and ranked is not None:
            accepted.append(ranked)
        else:
            skipped.append(
                {
                    "slug": str(raw.get("slug") or raw.get("id") or ""),
                    "title": str(raw.get("title") or ""),
                    "pool_usd": float(raw.get("prize_usd") or raw.get("bounty_usd") or 0.0),
                    "submission_count": int(raw.get("submission_count") or raw.get("entrants") or 0),
                    "reason": reason,
                }
            )
    accepted.sort(key=lambda r: (r.sniper_score, r.ev_density_usd, r.pool_usd), reverse=True)
    return {
        "accepted_count": len(accepted),
        "skipped_count": len(skipped),
        "accepted": [asdict(x) for x in accepted],
        "skipped": skipped,
    }


def fetch_live_bounties(api_url: str = "https://make.fun/api/bounties?status=open&limit=100", timeout: int = 15) -> list[dict[str, Any]]:
    req = urllib.request.Request(api_url, headers={"User-Agent": "makefun-agent-starter-kit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("bounties", "items", "data", "results"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Filter Make.fun bounties by sniper EV density.")
    parser.add_argument("--input", type=str, help="Path to local JSON list of bounties.")
    parser.add_argument("--live", action="store_true", help="Fetch open bounties live from make.fun API.")
    parser.add_argument("--min-pool", type=float, default=150.0, help="Minimum prize pool in USD (default: 150).")
    parser.add_argument("--max-entrants", type=int, default=400, help="Maximum entrants cap (default: 400).")
    parser.add_argument("--allow-subjective", action="store_true", help="Include subjective/comedy prompts.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")
    args = parser.parse_args(argv)

    if args.input:
        items = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if isinstance(items, dict):
            items = items.get("bounties") or items.get("items") or []
    elif args.live:
        items = fetch_live_bounties()
    else:
        parser.error("Provide --input <file.json> or --live")
        return 2

    res = filter_and_rank(
        items,
        min_pool_usd=args.min_pool,
        max_entrants=args.max_entrants,
        allow_subjective=args.allow_subjective,
    )
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print(f"Make.fun Sniper Filter | min_pool=${args.min_pool:g} | max_entrants={args.max_entrants}")
    print(f"Accepted: {res['accepted_count']} | Skipped: {res['skipped_count']}\n")
    for idx, row in enumerate(res["accepted"][:15], 1):
        det = "DET" if row["deterministic"] else "GEN"
        print(
            f"{idx:2d}. [{det}] {row['slug']} | ${row['pool_usd']:g} / {row['submission_count']} subs "
            f"(EV density ${row['ev_density_usd']:.2f}/entry, score={row['sniper_score']:.1f})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
