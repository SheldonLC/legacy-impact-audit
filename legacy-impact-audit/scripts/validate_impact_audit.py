#!/usr/bin/env python3
"""Deterministic gate validator for legacy-impact-audit artifacts."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


DEFAULT_WATCH_GLOBS = [
    "*.java",
    "*.xml",
    "*.properties",
    "*.sql",
    "*.jsp",
    "*.jspx",
    "*.groovy",
    "*.kt",
    "*.scala",
]


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except FileNotFoundError:
        raise SystemExit(f"missing required audit artifact: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON artifact {path}: {exc}")


def git_changed_files(root: Path, mode: str) -> list[str]:
    args_by_mode = {
        "staged": ["diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        "worktree": ["diff", "--name-only", "--diff-filter=ACMRT"],
        "all": ["diff", "HEAD", "--name-only", "--diff-filter=ACMRT"],
    }
    try:
        proc = subprocess.run(
            ["git", *args_by_mode[mode]],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def matches_any(path: str, globs: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    name = Path(normalized).name
    return any(fnmatch.fnmatch(normalized, glob) or fnmatch.fnmatch(name, glob) for glob in globs)


def newest_existing_mtime(root: Path, paths: Iterable[str]) -> float | None:
    mtimes = []
    for rel_path in paths:
        path = root / rel_path
        if path.exists():
            mtimes.append(path.stat().st_mtime)
    return max(mtimes) if mtimes else None


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    audit_dir = Path(args.audit_dir)
    if not audit_dir.is_absolute():
        audit_dir = root / audit_dir

    changed_files = git_changed_files(root, args.mode)
    watched_files = [path for path in changed_files if matches_any(path, args.watch_glob)]
    if not watched_files and not args.always_require:
        print("PASS: no watched source/config changes require an impact audit")
        return 0

    report = audit_dir / "impact-report.md"
    scan_json = audit_dir / "impact-scan.json"
    packet = audit_dir / "llm-packet.md"

    if not report.exists():
        return fail(f"impact report missing: {report}")
    if not packet.exists():
        return fail(f"LLM packet missing: {packet}")
    scan = read_json(scan_json)

    gate_status = scan.get("gate", {}).get("status")
    if gate_status == "REFINE_REQUIRED":
        return fail("impact audit is blocked by REFINE_REQUIRED; rerun with owner class/package/module narrowing")
    if gate_status != "PASS":
        return fail(f"unexpected impact audit gate status: {gate_status!r}")

    now = time.time()
    age_minutes = int((now - report.stat().st_mtime) / 60)
    if age_minutes > args.max_age_minutes:
        return fail(f"impact report is stale: {age_minutes} minutes old, limit is {args.max_age_minutes}")

    newest_change = newest_existing_mtime(root, watched_files)
    if newest_change and report.stat().st_mtime < newest_change:
        return fail("impact report is older than at least one watched changed file")

    if args.require_verdicts:
        verdict_file = Path(args.verdict_file)
        if not verdict_file.is_absolute():
            verdict_file = audit_dir / verdict_file
        if not verdict_file.exists():
            return fail(f"semantic verdict file missing: {verdict_file}")
        verdict_text = verdict_file.read_text(encoding="utf-8", errors="ignore")
        if "real_dependency" not in verdict_text and "possible_dependency" not in verdict_text:
            return fail(f"semantic verdict file does not contain dependency verdicts: {verdict_file}")

    print(
        "PASS: impact audit artifacts are present, fresh, and gate status is PASS "
        f"({len(watched_files)} watched changed files)"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate legacy-impact-audit artifacts for hooks or CI")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--audit-dir", default=".ai/legacy-impact-audit", help="Audit artifact directory")
    parser.add_argument("--mode", choices=["staged", "worktree", "all"], default="staged")
    parser.add_argument("--max-age-minutes", type=int, default=240)
    parser.add_argument("--watch-glob", action="append", default=DEFAULT_WATCH_GLOBS)
    parser.add_argument("--always-require", action="store_true", help="Require artifacts even when no watched diff exists")
    parser.add_argument("--require-verdicts", action="store_true", help="Require semantic verdict artifact")
    parser.add_argument("--verdict-file", default="semantic-verdict.md", help="Path relative to audit dir unless absolute")
    return parser


def main(argv: list[str] | None = None) -> int:
    return validate(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
