"""Pre-Submission Anti-Cheat & Bundle Budget Preflight Check.

Prevents the top 4 reasons Make.fun / GitHub bounty submissions get rejected:
  1. Hardcoded secrets / .env files committed in the bundle
  2. Size-budget overflow (e.g., 4KB / 8KB code golf & Tiny VM limits)
  3. Test-cheating patterns (pytest.skip, assert True stubs, monkeypatched graders)
  4. External network URLs in offline-only HTML/WebGL entries

Usage:
    python scripts/preflight_check.py --dir ./submission --max-bytes 8192 --offline-only
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FORBIDDEN_FILENAMES = {".env", ".env.local", "id_rsa", "makefun-keypair.json", "credentials.json"}
SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]
CHEAT_PATTERNS = [
    ("pytest_skip", re.compile(r"\bpytest\.skip\s*\(")),
    ("unittest_skip", re.compile(r"@unittest\.skip\b")),
    ("always_true_assert", re.compile(r"^\s*assert\s+True\s*(?:#.*)?$", re.MULTILINE)),
]
EXTERNAL_URL_RE = re.compile(r"https?://(?!localhost\b|127\.0\.0\.1\b)[^\s\"'<>]+", re.IGNORECASE)
IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "venv"}
TEXT_EXTS = {".py", ".js", ".mjs", ".ts", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".md", ".sh", ".rs", ".go"}


def run_preflight(
    root: Path,
    *,
    max_bytes: int | None = None,
    offline_only: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    issues: list[dict[str, Any]] = []
    total_bytes = 0
    file_count = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        file_count += 1
        size = path.stat().st_size
        total_bytes += size
        rel = "/".join(rel_parts)

        if path.name.lower() in FORBIDDEN_FILENAMES:
            issues.append({"severity": "CRITICAL", "rule": "forbidden_secret_file", "file": rel})
            continue

        if path.suffix.lower() not in TEXT_EXTS or size > 2_000_000:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for rule_name, rx in SECRET_PATTERNS:
            if rx.search(text):
                issues.append({"severity": "CRITICAL", "rule": rule_name, "file": rel})

        if "test" in rel.lower():
            for rule_name, rx in CHEAT_PATTERNS:
                if rx.search(text):
                    issues.append({"severity": "HIGH", "rule": rule_name, "file": rel})

        if offline_only and path.suffix.lower() in {".html", ".js", ".mjs", ".ts", ".css"}:
            hits = EXTERNAL_URL_RE.findall(text)
            if hits:
                issues.append(
                    {
                        "severity": "HIGH",
                        "rule": "external_url_in_offline_entry",
                        "file": rel,
                        "sample": hits[0][:120],
                    }
                )

    if max_bytes is not None and total_bytes > max_bytes:
        issues.append(
            {
                "severity": "CRITICAL",
                "rule": "bundle_size_exceeded",
                "file": ".",
                "detail": f"{total_bytes} bytes > {max_bytes} byte limit",
            }
        )

    passed = len(issues) == 0
    return {
        "ok": passed,
        "root": str(root),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_bytes": max_bytes,
        "issue_count": len(issues),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preflight submission audit for Make.fun & OSS bounties.")
    parser.add_argument("--dir", default=".", help="Submission directory.")
    parser.add_argument("--max-bytes", type=int, default=None, help="Maximum total bundle size in bytes.")
    parser.add_argument("--offline-only", action="store_true", help="Reject external http(s) URLs in web assets.")
    args = parser.parse_args(argv)

    report = run_preflight(Path(args.dir), max_bytes=args.max_bytes, offline_only=args.offline_only)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
