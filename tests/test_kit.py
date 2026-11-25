from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.local_grader_loop import evaluate_and_pin, parse_score
from scripts.preflight_check import run_preflight
from scripts.sniper_filter import filter_and_rank


def test_sniper_filter_rejects_crowded_and_subjective_traps() -> None:
    sample = [
        {"slug": "gta6-crowded", "title": "Make GTA 6", "prize_usd": 1666, "submission_count": 11652, "harness_kind": "judge"},
        {"slug": "comedy-joke", "title": "One-line office joke sprint", "prize_usd": 200, "submission_count": 15, "harness_kind": "judge"},
        {"slug": "tiny-stack-vm", "title": "Tiny Stack VM 8KB", "prize_usd": 300, "submission_count": 85, "harness_kind": "command"},
        {"slug": "rust-parser", "title": "Zero-Copy Rust Parser Benchmark", "prize_usd": 500, "submission_count": 42, "harness_kind": "command"},
    ]
    res = filter_and_rank(sample, min_pool_usd=150, max_entrants=400)
    assert res["accepted_count"] == 2
    assert res["skipped_count"] == 2
    assert res["accepted"][0]["slug"] == "rust-parser"
    reasons = {row["slug"]: row["reason"] for row in res["skipped"]}
    assert "crowded_arena" in reasons["gta6-crowded"]
    assert reasons["comedy-joke"] == "subjective_comedy_trap"


def test_local_grader_loop_pins_best_and_blocks_regression(tmp_path: Path) -> None:
    pin = tmp_path / ".grader_pin.json"
    py = f'"{sys.executable}"'
    r1 = evaluate_and_pin(f"{py} -c \"print('SCORE=850.5')\"", cwd=tmp_path, pin_file=pin, mode="max")
    assert r1["ok"] is True
    assert r1["improved"] is True
    assert r1["best_score"] == 850.5

    r2 = evaluate_and_pin(f"{py} -c \"print('SCORE=790.0')\"", cwd=tmp_path, pin_file=pin, mode="max")
    assert r2["ok"] is True
    assert r2["improved"] is False
    assert r2["regression_blocked"] is True
    assert r2["best_score"] == 850.5

    assert parse_score('{"median_us": 280.4}', json_key="median_us") == 280.4


def test_preflight_catches_secrets_size_and_external_urls(tmp_path: Path) -> None:
    (tmp_path / "app.html").write_text('<script src="https://cdn.example.com/lib.js"></script>', encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=123", encoding="utf-8")
    (tmp_path / "test_demo.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")

    rep = run_preflight(tmp_path, max_bytes=32, offline_only=True)
    assert rep["ok"] is False
    rules = {i["rule"] for i in rep["issues"]}
    assert {"forbidden_secret_file", "external_url_in_offline_entry", "always_true_assert", "bundle_size_exceeded"} <= rules

    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    (clean_dir / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    rep_ok = run_preflight(clean_dir, max_bytes=1024, offline_only=True)
    assert rep_ok["ok"] is True
