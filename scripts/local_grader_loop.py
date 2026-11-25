"""Deterministic Local Grader Loop with Anti-Regress Commit Pinning.

Runs a grading command repeatedly or on a single candidate, parses a numeric score
(higher-is-better or lower-is-better for latency benchmarks), and pins the best
git commit hash so your agent never submits a regressed round.

Usage:
    python scripts/local_grader_loop.py --cmd "python grade.py" --regex "SCORE=([0-9.]+)"
    python scripts/local_grader_loop.py --cmd "node bench.js" --json-key median_us --mode min
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_score(output: str, *, regex: str | None = None, json_key: str | None = None) -> float:
    text = str(output or "").strip()
    if json_key:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                if json_key in obj:
                    return float(obj[json_key])
            except Exception:
                continue
        obj = json.loads(text)
        return float(obj[json_key])
    pattern = regex or r"(?:score|SCORE|Score)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"
    matches = re.findall(pattern, text)
    if not matches:
        raise ValueError(f"Could not extract numeric score using pattern: {pattern}")
    return float(matches[-1])


def is_improvement(candidate: float, best: float | None, mode: str = "max") -> bool:
    if best is None:
        return True
    return candidate < best if mode == "min" else candidate > best


def current_git_head(cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "uncommitted"


def evaluate_and_pin(
    cmd: str,
    *,
    cwd: Path,
    pin_file: Path,
    mode: str = "max",
    regex: str | None = None,
    json_key: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        return {
            "ok": False,
            "pinned": False,
            "returncode": proc.returncode,
            "error": "Grader command failed",
            "output_tail": combined.strip()[-800:],
        }

    score = parse_score(combined, regex=regex, json_key=json_key)
    commit = current_git_head(cwd)
    prev: dict[str, Any] = {}
    if pin_file.exists():
        try:
            prev = json.loads(pin_file.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

    prev_best = float(prev["best_score"]) if "best_score" in prev else None
    improved = is_improvement(score, prev_best, mode=mode)
    now_iso = datetime.now(timezone.utc).isoformat()

    history = list(prev.get("history") or [])
    history.append({"at": now_iso, "commit": commit, "score": score, "improved": improved})

    state = {
        "mode": mode,
        "best_score": score if improved else prev_best,
        "best_commit": commit if improved else prev.get("best_commit", commit),
        "last_score": score,
        "last_commit": commit,
        "updated_at": now_iso,
        "history": history[-30:],
    }
    pin_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "improved": improved,
        "score": score,
        "best_score": state["best_score"],
        "best_commit": state["best_commit"],
        "commit": commit,
        "regression_blocked": not improved and prev_best is not None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local grader and pin best non-regressing commit.")
    parser.add_argument("--cmd", required=True, help="Shell command that prints score.")
    parser.add_argument("--cwd", default=".", help="Working directory.")
    parser.add_argument("--pin-file", default=".grader_pin.json", help="Path to pin state JSON.")
    parser.add_argument("--mode", choices=("max", "min"), default="max", help="Maximize score or minimize latency.")
    parser.add_argument("--regex", default=None, help="Regex with 1 numeric capture group.")
    parser.add_argument("--json-key", default=None, help="JSON key to extract numeric score.")
    parser.add_argument("--timeout", type=int, default=120, help="Grader timeout in seconds.")
    args = parser.parse_args(argv)

    cwd = Path(args.cwd).resolve()
    pin_file = (cwd / args.pin_file).resolve() if not Path(args.pin_file).is_absolute() else Path(args.pin_file)
    res = evaluate_and_pin(
        args.cmd,
        cwd=cwd,
        pin_file=pin_file,
        mode=args.mode,
        regex=args.regex,
        json_key=args.json_key,
        timeout=args.timeout,
    )
    print(json.dumps(res, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
