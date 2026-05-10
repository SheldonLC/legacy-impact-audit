#!/usr/bin/env python3
"""Low-token impact audit funnel for legacy Java repositories.

The script does deterministic work only: rg retrieval, filtering, heuristic
ranking, snippet extraction, report generation, and cache-key calculation.
LLM semantic confirmation is intentionally left to the agent after this script
has reduced the candidate set.
"""

from __future__ import annotations

import argparse
import codecs
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


DEFAULT_INCLUDE_GLOBS = [
    "*.java",
    "*.jsp",
    "*.jspx",
    "*.xml",
    "*.properties",
    "*.sql",
    "*.groovy",
    "*.kt",
    "*.scala",
]

DEFAULT_EXCLUDE_GLOBS = [
    "!**/.git/**",
    "!**/node_modules/**",
    "!**/target/**",
    "!**/build/**",
    "!**/dist/**",
    "!**/out/**",
    "!**/coverage/**",
    "!**/vendor/**",
    "!**/generated/**",
    "!**/build.xml",
    "!**/*.class",
    "!**/*.jar",
    "!**/*.war",
    "!**/*.ear",
    "!**/*.min.js",
]

DEFAULT_ENCODING = "utf-8"

COMMON_SYMBOLS = {
    "add",
    "build",
    "calculate",
    "check",
    "compare",
    "convert",
    "create",
    "delete",
    "doexecute",
    "equals",
    "execute",
    "find",
    "get",
    "handle",
    "hashcode",
    "init",
    "load",
    "main",
    "parse",
    "process",
    "query",
    "remove",
    "run",
    "save",
    "set",
    "toString".lower(),
    "update",
    "validate",
}

LOG_CALL_RE = re.compile(
    r"\b(?:log|logger|LOG|LOGGER)\s*\.\s*(?:trace|debug|info|warn|error|fatal)\s*\(",
)
COMMENT_LINE_RE = re.compile(r"^\s*(?://|/\*|\*|<!--|#)")
PACKAGE_RE = re.compile(r"(?m)^\s*package\s+([\w.]+)\s*;")
IMPORT_RE = re.compile(r"(?m)^\s*import\s+(static\s+)?([\w.*]+)\s*;")
METHOD_DECL_PREFIX_RE = re.compile(
    r"\b(?:public|protected|private|static|final|abstract|synchronized|native|default|strictfp)\b"
)


@dataclass
class Match:
    path: str
    line_number: int
    column: int
    line: str


@dataclass
class FileCandidate:
    path: str
    score: int = 0
    priority: str = "BACKGROUND"
    reasons: list[str] = field(default_factory=list)
    match_lines: list[int] = field(default_factory=list)
    snippets: list[dict[str, Any]] = field(default_factory=list)
    file_kind: str = "unknown"
    package: str | None = None
    imports_owner: bool = False
    static_imports_symbol: bool = False
    owner_class_referenced: bool = False
    same_package: bool = False
    call_shape_count: int = 0
    string_only_count: int = 0
    file_hash: str | None = None


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def sha1_file(path: Path) -> str | None:
    try:
        h = hashlib.sha1()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def normalize_encoding(encoding: str | None) -> str:
    if not encoding or encoding.lower() == "auto":
        return DEFAULT_ENCODING
    return encoding


def validate_encoding(encoding: str | None) -> None:
    try:
        codecs.lookup(normalize_encoding(encoding))
    except LookupError:
        raise SystemExit(f"Unsupported text encoding: {encoding}")


def read_text(path: Path, encoding: str | None = DEFAULT_ENCODING) -> str:
    try:
        return path.read_text(encoding=normalize_encoding(encoding), errors="replace")
    except OSError:
        return ""


def resolve_path(path_arg: str | None, repo_root: Path, search_root: Path) -> Path | None:
    if not path_arg:
        return None
    path = Path(path_arg)
    if path.is_absolute():
        return path.resolve()
    candidates = [repo_root / path, search_root / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (repo_root / path).resolve()


def _is_rg_available() -> bool:
    try:
        subprocess.run(["rg", "--version"], capture_output=True, check=False, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_search(
    root: Path,
    symbol: str,
    include_globs: list[str],
    exclude_globs: list[str],
    source_encoding: str,
) -> list[Match]:
    """Run rg for structured results, with grep fallback on systems without ripgrep."""
    if _is_rg_available():
        return _run_rg(root, symbol, include_globs, exclude_globs, source_encoding)
    return _run_grep_fallback(root, symbol, include_globs, exclude_globs)


def _run_rg(
    root: Path,
    symbol: str,
    include_globs: list[str],
    exclude_globs: list[str],
    source_encoding: str,
) -> list[Match]:
    cmd = [
        "rg",
        "--json",
        "--line-number",
        "--column",
        "--no-heading",
        "--color",
        "never",
        "--fixed-strings",
    ]
    if source_encoding.lower() != "auto":
        cmd.extend(["--encoding", source_encoding])
    for glob in include_globs:
        cmd.extend(["-g", glob])
    for glob in exclude_globs:
        cmd.extend(["-g", glob])
    cmd.extend([symbol, str(root)])

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            encoding=DEFAULT_ENCODING,
            errors="replace",
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        raise SystemExit("rg is required but was not found in PATH")

    if proc.returncode not in (0, 1):
        raise SystemExit(proc.stderr.strip() or "rg failed")

    matches: list[Match] = []
    for raw_line in proc.stdout.splitlines():
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "match":
            continue
        data = event.get("data", {})
        path = data.get("path", {}).get("text", "")
        line = data.get("lines", {}).get("text", "")
        submatches = data.get("submatches") or [{}]
        column = int(submatches[0].get("start", 0)) + 1
        matches.append(
            Match(
                path=os.path.normpath(path),
                line_number=int(data.get("line_number", 0)),
                column=column,
                line=line.rstrip("\n\r"),
            )
        )
    return matches


def _run_grep_fallback(
    root: Path,
    symbol: str,
    include_globs: list[str],
    exclude_globs: list[str],
) -> list[Match]:
    """Fallback: use grep when ripgrep is not available (pre-installed on all Unix)."""
    # Build grep command: grep -rnF <symbol> <root>
    cmd: list[str] = ["grep", "-rnF", symbol, str(root)]

    # Add --include for each glob
    for glob_pat in include_globs:
        cmd.extend(["--include", glob_pat])

    # Exclude standard noise directories
    for noise_dir in [".git", "node_modules", "target", "build", "dist", "out", "coverage", "vendor", "generated", "__pycache__"]:
        cmd.extend(["--exclude-dir", noise_dir])

    # Additional user exclude patterns
    for glob_pat in exclude_globs:
        clean = glob_pat.lstrip("!")
        if clean.count("/") <= 1 and not clean.startswith("*."):
            cmd.extend(["--exclude-dir", clean.split("/")[0]])
        elif clean.startswith("*."):
            cmd.extend(["--exclude", clean])

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            encoding=DEFAULT_ENCODING,
            errors="replace",
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        raise SystemExit(
            "Neither rg nor grep was found in PATH.\n"
            "  Install ripgrep:\n"
            "    macOS:  brew install ripgrep\n"
            "    Linux:  apt install ripgrep   (or: dnf install ripgrep)\n"
            "    Windows: https://github.com/BurntSushi/ripgrep/releases\n"
            "  Or ensure grep is available (pre-installed on macOS/Linux)."
        )

    if proc.returncode not in (0, 1):
        raise SystemExit(proc.stderr.strip() or "grep failed")

    # Parse grep output: file:lineno:content
    matches: list[Match] = []
    for raw_line in proc.stdout.splitlines():
        # Format: path:lineno:line_content
        parts = raw_line.split(":", 2)
        if len(parts) < 3:
            continue
        path_str, lineno_str, line_content = parts
        try:
            lineno = int(lineno_str)
        except ValueError:
            continue
        # Skip binary file markers
        if path_str == "Binary file" and "matches" in line_content:
            continue
        matches.append(
            Match(
                path=os.path.normpath(path_str),
                line_number=lineno,
                column=0,  # grep doesn't report column
                line=line_content.rstrip("\n\r"),
            )
        )
    return matches


def is_noise_line(line: str) -> bool:
    if COMMENT_LINE_RE.search(line):
        return True
    if LOG_CALL_RE.search(line):
        return True
    return False


def classify_file(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    name = Path(normalized).name
    suffix = Path(normalized).suffix
    if "/test/" in normalized or name.endswith("test.java") or name.endswith("tests.java"):
        return "test"
    if suffix == ".java":
        return "java"
    if suffix in {".jsp", ".jspx"}:
        return "jsp"
    if suffix == ".xml":
        return "xml-config"
    if suffix == ".sql":
        return "sql"
    if suffix == ".properties":
        return "properties"
    return suffix.lstrip(".") or "unknown"


def extract_java_metadata(text: str) -> tuple[str | None, set[str], set[str]]:
    package_match = PACKAGE_RE.search(text)
    package_name = package_match.group(1) if package_match else None
    imports: set[str] = set()
    static_imports: set[str] = set()
    for match in IMPORT_RE.finditer(text):
        is_static = bool(match.group(1))
        value = match.group(2)
        if is_static:
            static_imports.add(value)
        else:
            imports.add(value)
    return package_name, imports, static_imports


def is_definition_line(line: str, symbol: str) -> bool:
    escaped = re.escape(symbol)
    if not re.search(rf"\b{escaped}\s*\(", line):
        return False
    if not METHOD_DECL_PREFIX_RE.search(line):
        return False
    # Declarations usually do not have a method receiver before the symbol.
    prefix = line[: line.find(symbol)]
    return "." not in prefix[-32:]


def has_call_shape(line: str, symbol: str) -> bool:
    escaped = re.escape(symbol)
    call_re = re.compile(rf"(?<![\w$])(?:[\w$]+\s*\.\s*)?{escaped}\s*\(")
    return bool(call_re.search(line)) and not is_definition_line(line, symbol)


def is_string_only_match(line: str, symbol: str) -> bool:
    if has_call_shape(line, symbol):
        return False
    escaped = re.escape(symbol)
    quoted = re.search(rf"['\"][^'\"]*{escaped}[^'\"]*['\"]", line)
    xml_attr = re.search(rf"\b(?:name|method|property|ref|value|id)\s*=\s*['\"]{escaped}['\"]", line)
    return bool(quoted or xml_attr)


def line_window(lines: list[str], line_number: int, context: int) -> dict[str, Any]:
    start = max(1, line_number - context)
    end = min(len(lines), line_number + context)
    body = []
    for idx in range(start, end + 1):
        marker = ">" if idx == line_number else " "
        body.append(f"{marker} {idx}: {lines[idx - 1]}")
    return {"start": start, "end": end, "text": "\n".join(body)}


def unique_sorted(values: Iterable[int]) -> list[int]:
    return sorted(set(values))


def rank_candidates(
    search_root: Path,
    matches: list[Match],
    symbol: str,
    owner_class: str | None,
    owner_package: str | None,
    definition_abs: Path | None,
    context_lines: int,
    source_encoding: str,
) -> list[FileCandidate]:
    by_file: dict[str, list[Match]] = {}
    for match in matches:
        if is_noise_line(match.line):
            continue
        by_file.setdefault(match.path, []).append(match)

    candidates: list[FileCandidate] = []

    for path_text, file_matches in by_file.items():
        path = Path(path_text)
        try:
            rel_or_abs = path if path.is_absolute() else search_root / path
            abs_path = rel_or_abs.resolve()
        except OSError:
            abs_path = search_root / path

        text = read_text(abs_path, source_encoding)
        lines = text.splitlines()
        package_name, imports, static_imports = extract_java_metadata(text)
        file_kind = classify_file(path_text)
        candidate = FileCandidate(path=path_text, file_kind=file_kind, package=package_name)
        candidate.match_lines = unique_sorted(m.line_number for m in file_matches)
        candidate.file_hash = sha1_file(abs_path)

        owner_import_name = None
        if owner_package and owner_class:
            owner_import_name = f"{owner_package}.{owner_class}"

        if owner_class:
            candidate.owner_class_referenced = owner_class in text
        if owner_import_name and owner_import_name in imports:
            candidate.imports_owner = True
        elif owner_class and any(item.endswith(f".{owner_class}") for item in imports):
            candidate.imports_owner = True
        if owner_class and any(item.endswith(f".{owner_class}.{symbol}") or item.endswith(f".{symbol}") for item in static_imports):
            candidate.static_imports_symbol = True
        if owner_package and package_name:
            candidate.same_package = package_name == owner_package or package_name.startswith(owner_package + ".")

        call_lines = [m for m in file_matches if has_call_shape(m.line, symbol)]
        string_only = [m for m in file_matches if is_string_only_match(m.line, symbol)]
        candidate.call_shape_count = len(call_lines)
        candidate.string_only_count = len(string_only)

        score = 5
        reasons: list[str] = []

        if candidate.call_shape_count:
            gain = min(45, 20 + candidate.call_shape_count * 5)
            score += gain
            reasons.append(f"java-call-shape:{candidate.call_shape_count}")
        if candidate.static_imports_symbol:
            score += 40
            reasons.append("static-imports-symbol")
        if candidate.imports_owner:
            score += 30
            reasons.append("imports-owner-class")
        if candidate.owner_class_referenced:
            score += 18
            reasons.append("references-owner-class")
        if candidate.same_package:
            score += 12
            reasons.append("same-package")
        if owner_package:
            package_path = owner_package.replace(".", "/").lower()
            if package_path and package_path in path_text.replace("\\", "/").lower():
                score += 8
                reasons.append("same-package-path")

        if candidate.string_only_count and not candidate.call_shape_count:
            score -= min(35, 15 + candidate.string_only_count * 5)
            reasons.append(f"string-only:{candidate.string_only_count}")
        if file_kind in {"xml-config", "properties", "sql"}:
            score -= 10
            reasons.append(file_kind)
        if file_kind == "test":
            score -= 6
            reasons.append("test-file")
        if definition_abs and abs_path == definition_abs:
            score -= 20
            reasons.append("definition-file")
        if not candidate.call_shape_count and not candidate.imports_owner and not candidate.static_imports_symbol:
            score -= 10
            reasons.append("no-strong-java-link")

        candidate.score = max(score, 0)
        candidate.reasons = reasons or ["text-match"]
        if candidate.score >= 70:
            candidate.priority = "HIGH"
        elif candidate.score >= 40:
            candidate.priority = "MEDIUM"
        elif candidate.score >= 15:
            candidate.priority = "LOW"
        else:
            candidate.priority = "BACKGROUND"

        for line_number in candidate.match_lines[:5]:
            if lines and 1 <= line_number <= len(lines):
                candidate.snippets.append(line_window(lines, line_number, context_lines))
            else:
                candidate.snippets.append(
                    {"start": line_number, "end": line_number, "text": f"> {line_number}: <unavailable>"}
                )

        candidates.append(candidate)

    candidates.sort(key=lambda item: (-item.score, item.path))
    return candidates


def git_value(root: Path, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(root),
            text=True,
            encoding=DEFAULT_ENCODING,
            errors="replace",
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def compute_cache_key(
    repo_root: Path,
    symbol: str,
    owner_class: str | None,
    owner_package: str | None,
    definition_file: str | None,
    definition_abs: Path | None,
    candidates: list[FileCandidate],
    source_encoding: str,
) -> str:
    definition_hash = sha1_file(definition_abs) if definition_abs else None
    payload = {
        "symbol": symbol,
        "owner_class": owner_class,
        "owner_package": owner_package,
        "definition_file": definition_file,
        "encoding": source_encoding,
        "definition_hash": definition_hash,
        "git_head": git_value(repo_root, ["rev-parse", "HEAD"]),
        "git_diff_hash": sha1_text(git_value(repo_root, ["diff", "--", "*.java", "*.xml", "*.properties", "*.sql"]) or ""),
        "candidates": [
            {"path": item.path, "hash": item.file_hash, "lines": item.match_lines}
            for item in candidates
            if item.priority in {"HIGH", "MEDIUM", "LOW"}
        ],
    }
    return sha1_text(json.dumps(payload, sort_keys=True, ensure_ascii=True))


def load_cache(cache_file: Path) -> dict[str, Any]:
    if not cache_file.exists():
        return {"version": 1, "entries": {}}
    try:
        return json.loads(read_text(cache_file))
    except json.JSONDecodeError:
        return {"version": 1, "entries": {}}


def parse_cache_time(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def prune_cache(cache: dict[str, Any], max_entries: int, ttl_days: int) -> int:
    entries = cache.setdefault("entries", {})
    original_count = len(entries)
    if ttl_days > 0:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=ttl_days)
        for key, value in list(entries.items()):
            updated_at = value.get("updated_at") if isinstance(value, dict) else None
            if parse_cache_time(updated_at) < cutoff:
                entries.pop(key, None)
    if max_entries > 0 and len(entries) > max_entries:
        sorted_items = sorted(
            entries.items(),
            key=lambda item: parse_cache_time(item[1].get("updated_at") if isinstance(item[1], dict) else None),
            reverse=True,
        )
        keep = {key for key, _value in sorted_items[:max_entries]}
        for key in list(entries):
            if key not in keep:
                entries.pop(key, None)
    return original_count - len(entries)


def gate_status(
    symbol: str,
    raw_count: int,
    filtered_count: int,
    owner_class: str | None,
    owner_package: str | None,
    raw_limit: int,
    generic_limit: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    normalized = symbol.lower()
    generic = len(symbol) <= 3 or normalized in COMMON_SYMBOLS
    if generic:
        reasons.append("generic-or-short-symbol")
    if raw_count > raw_limit:
        reasons.append(f"raw-count>{raw_limit}")
    if generic and filtered_count > generic_limit and not (owner_class or owner_package):
        reasons.append("generic-symbol-needs-owner-class-or-package")
    if raw_count > raw_limit or (generic and filtered_count > generic_limit and not (owner_class or owner_package)):
        return "REFINE_REQUIRED", reasons
    return "PASS", reasons or ["symbol-frequency-acceptable"]


def candidate_to_dict(candidate: FileCandidate) -> dict[str, Any]:
    return {
        "path": candidate.path,
        "score": candidate.score,
        "priority": candidate.priority,
        "reasons": candidate.reasons,
        "match_lines": candidate.match_lines,
        "file_kind": candidate.file_kind,
        "package": candidate.package,
        "imports_owner": candidate.imports_owner,
        "static_imports_symbol": candidate.static_imports_symbol,
        "owner_class_referenced": candidate.owner_class_referenced,
        "same_package": candidate.same_package,
        "call_shape_count": candidate.call_shape_count,
        "string_only_count": candidate.string_only_count,
        "file_hash": candidate.file_hash,
        "snippets": candidate.snippets,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def extract_module(file_path: str, search_root: Path) -> str:
    """Extract the top-level module name from a file path relative to search_root."""
    try:
        rel = Path(file_path).relative_to(search_root)
        parts = rel.parts
        if parts:
            return parts[0]
    except (ValueError, OSError):
        pass
    return "unknown"


def risk_emoji(priority: str) -> str:
    """Return a risk emoji for a priority tier."""
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪", "BACKGROUND": "⚫"}.get(priority, "")


_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "BACKGROUND": 3}

def _module_sort_key(item: tuple[str, int, int]) -> tuple[int, int, int, str]:
    """Sort modules: highest risk first, then by call count desc, then module name."""
    module, count, worst_priority = item
    return (worst_priority, -count, module)


def write_report(
    path: Path,
    payload: dict[str, Any],
    top_candidates: list[FileCandidate],
    search_root: Path | None = None,
) -> None:
    target = payload["target"]
    gate = payload["gate"]
    cache = payload["cache"]
    lines = [
        "# Legacy Impact Audit Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "## Target",
        "",
        f"- Symbol: `{target['symbol']}`",
        f"- Owner class: `{target.get('owner_class') or ''}`",
        f"- Owner package: `{target.get('owner_package') or ''}`",
        f"- Definition file: `{target.get('definition_file') or ''}`",
        "",
        "## Gate",
        "",
        f"- Status: `{gate['status']}`",
        f"- Reasons: {', '.join(gate['reasons'])}",
        f"- Raw matches: `{payload['counts']['raw_matches']}`",
        f"- Filtered matches: `{payload['counts']['filtered_matches']}`",
        f"- Candidate files: `{payload['counts']['candidate_files']}`",
        f"- Cache key: `{cache['key']}`",
        f"- Cache status: `{cache['status']}`",
        "",
    ]
    if gate["status"] == "REFINE_REQUIRED":
        lines.extend(
            [
                "## Required Refinement",
                "",
                "Do not call the LLM on this raw result set. Re-run with owner information or a narrower module.",
                "",
                "Suggested refinements:",
                "",
                "- Add `--owner-class`.",
                "- Add `--owner-package`.",
                "- Add `--module-path` to restrict the root/module.",
                "- Use the exact changed method rather than a generic wrapper method.",
                "",
            ]
        )

    if search_root is not None:
        for item in top_candidates:
            item._module = extract_module(item.path, search_root)
    else:
        for item in top_candidates:
            item._module = ""

    # ── Blast Radius Summary (module grouping) ──
    if top_candidates and any(getattr(c, "_module", "") for c in top_candidates):
        module_counts: dict[str, int] = {}
        module_best: dict[str, int] = {}
        module_high: dict[str, int] = {}
        for c in top_candidates:
            module_name = getattr(c, "_module", "")
            if not module_name:
                continue
            module_counts[module_name] = module_counts.get(module_name, 0) + 1
            module_high[module_name] = module_high.get(module_name, 0) + (1 if c.priority == "HIGH" else 0)
            current_best = module_best.get(module_name, _PRIORITY_ORDER.get("BACKGROUND", 99))
            module_best[module_name] = min(current_best, _PRIORITY_ORDER.get(c.priority, 99))

        sorted_modules = sorted(
            [(m, module_counts[m], module_best[m], module_high[m]) for m in module_counts],
            key=lambda x: (x[2], -x[1], x[0]),
        )

        lines.extend([
            "",
            "## Blast Radius",
            "",
            f"**{len(sorted_modules)} module(s)** affected. {len(top_candidates)} candidate file(s) total.",
            "",
        ])

        # ASCII tree
        source_module = extract_module(target.get("definition_file", ""), search_root) if target.get("definition_file") else ""
        if source_module:
            root_label = f"{source_module} (source)"
        else:
            root_label = target.get("owner_class", "Source")

        lines.append("```text")
        lines.append(root_label)
        for idx, (module_name, count, worst_pri, high_count) in enumerate(sorted_modules):
            is_last = idx == len(sorted_modules) - 1
            prefix = " └── " if is_last else " ├── "
            emoji = ""
            for pri_name, pri_val in _PRIORITY_ORDER.items():
                if worst_pri == pri_val:
                    emoji = risk_emoji(pri_name)
                    break
            extra = f" ({count} file" + ("s" if count > 1 else "") + f", {high_count} HIGH)" if high_count > 0 else f" ({count} file" + ("s" if count > 1 else "") + ")"
            lines.append(f"{prefix}{emoji} {module_name}{extra}")
        lines.append("```")
        lines.append("")

        # Module summary table
        lines.extend([
            "### Module Summary",
            "",
            "| Module | Files | HIGH | Risk |",
            "| --- | ---: | ---: | --- |",
        ])
        for module_name, count, worst_pri, high_count in sorted_modules:
            emoji = ""
            for pri_name, pri_val in _PRIORITY_ORDER.items():
                if worst_pri == pri_val:
                    emoji = risk_emoji(pri_name)
                    break
            lines.append(f"| {module_name} | {count} | {high_count} | {emoji} |")
        lines.append("")

    # ── Ranked Candidates Table ──
    lines.extend(
        [
            "## Ranked Candidates",
            "",
            "| Rank | Risk | Score | Module | File | Lines | Reasons |",
            "| ---: | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for index, item in enumerate(top_candidates, start=1):
        module_name = getattr(item, "_module", "")
        lines.append(
            f"| {index} | {risk_emoji(item.priority)} {item.priority} | {item.score} |"
            f" {module_name} | `{md_escape(item.path)}` | "
            f"{md_escape(','.join(str(x) for x in item.match_lines[:8]))} | "
            f"{md_escape(', '.join(item.reasons))} |"
        )
    lines.extend(
        [
            "",
            "## LLM Step",
            "",
            "Use `llm-packet.md` for semantic confirmation. Classify each candidate as "
            "`real_dependency`, `possible_dependency`, `not_dependency`, or `needs_manual_check`.",
            "",
            "## Residual Risks",
            "",
            "- Reflection, dynamic proxies, XML wiring, runtime string dispatch, overloaded same-name methods, and generated code may need manual checks.",
            "- L1 is the default scope. Expand to L2 only after confirmed L1 dependencies cross a public or core business boundary.",
            "",
        ]
    )
    path.write_text("\n".join(str(line) for line in lines if line is not None), encoding="utf-8")


def write_llm_packet(path: Path, payload: dict[str, Any], top_candidates: list[FileCandidate]) -> None:
    target = payload["target"]
    lines = [
        "# LLM Semantic Confirmation Packet",
        "",
        "You are verifying Java legacy-code impact. Decide whether each candidate is a real logical dependency of the changed method.",
        "",
        "## Target",
        "",
        f"- Symbol: `{target['symbol']}`",
        f"- Owner class: `{target.get('owner_class') or ''}`",
        f"- Owner package: `{target.get('owner_package') or ''}`",
        f"- Definition file: `{target.get('definition_file') or ''}`",
        "",
        "## Required Output",
        "",
        "For each candidate return: candidate number, verdict, confidence `high|medium|low`, reason, and recommended test/manual check.",
        "",
        "Allowed verdicts: `real_dependency`, `possible_dependency`, `not_dependency`, `needs_manual_check`.",
        "",
        "## Candidates",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.extend(
            [
                f"### Candidate {index}: {item.path}",
                "",
                f"- Priority: `{item.priority}`",
                f"- Score: `{item.score}`",
                f"- Lines: `{', '.join(str(x) for x in item.match_lines)}`",
                f"- Heuristic reasons: `{', '.join(item.reasons)}`",
                "",
            ]
        )
        for snippet_index, snippet in enumerate(item.snippets, start=1):
            lines.extend(
                [
                    f"Snippet {snippet_index} lines {snippet['start']}-{snippet['end']}:",
                    "",
                    "```text",
                    snippet["text"],
                    "```",
                    "",
                ]
            )
    path.write_text("\n".join(str(line) for line in lines if line is not None), encoding="utf-8")


def default_output_dir(root: Path) -> Path:
    """Generate timestamped output dir: LEGACY_IMPACT_RESULTS/YYYYMMDD-NN/"""
    base = root / "LEGACY_IMPACT_RESULTS"
    today = dt.date.today().strftime("%Y%m%d")
    base.mkdir(parents=True, exist_ok=True)
    existing = sorted(base.glob(f"{today}-*")) if base.exists() else []
    seq = 1
    if existing:
        try:
            nums = [int(d.name.split("-")[-1]) for d in existing if d.name.startswith(today)]
            seq = max(nums) + 1 if nums else 1
        except (ValueError, IndexError):
            seq = 1
    return base / f"{today}-{seq:02d}"


def write_html_report(
    path: Path,
    payload: dict[str, Any],
    top_candidates: list[FileCandidate],
    all_candidates: list[FileCandidate],
    search_root: Path | None = None,
) -> None:
    """Generate a standalone, clean HTML report."""
    target = payload["target"]
    gate = payload["gate"]

    def hescape(text: str) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    # Module summary uses ALL candidates, not just top N
    modules: dict[str, dict[str, int]] = {}
    for item in all_candidates:
        mod = extract_module(item.path, search_root) if search_root else ""
        if mod not in modules:
            modules[mod] = {"files": 0, "high": 0}
        modules[mod]["files"] += 1
        if item.priority == "HIGH":
            modules[mod]["high"] += 1

    sorted_mods = sorted(modules.items(), key=lambda x: (-x[1]["high"], -x[1]["files"]))

    module_rows = ""
    for mod_name, m in sorted_mods:
        emoji = "🔴" if m["high"] > 0 else "⚫"
        module_rows += f"<tr><td>{hescape(mod_name)}</td><td>{m['files']}</td><td>{m['high']}</td><td>{emoji}</td></tr>\n"

    # Candidate rows: show ALL HIGH/MEDIUM, truncate LOW/BACKGROUND at limit
    display_candidates = []
    truncated_count = 0
    # Always include all HIGH + MEDIUM
    for item in all_candidates:
        if item.priority in ("HIGH", "MEDIUM"):
            display_candidates.append(item)
    # Fill remaining slots with LOW/BACKGROUND up to the limit
    low_fill = [item for item in all_candidates if item.priority not in ("HIGH", "MEDIUM")]
    total_high_med = len(display_candidates)
    total_low_bg = len(low_fill)
    # Use max(len(display_candidates), min_limit) so HIGH+MEDIUM are never cut
    display_limit = max(len(display_candidates), len(top_candidates))
    for item in low_fill[:display_limit - len(display_candidates)]:
        display_candidates.append(item)
    if total_low_bg > (display_limit - total_high_med):
        truncated_count = total_low_bg - (display_limit - total_high_med)

    candidate_rows = ""
    for idx, item in enumerate(display_candidates, start=1):
        mod = extract_module(item.path, search_root) if search_root else ""
        file_url = f"file:///{item.path.replace(chr(92), '/')}"
        file_link = f'<a href="{file_url}" target="_blank" title="Open in editor">{hescape(item.path)}</a>'
        candidate_rows += (
            f'<tr class="pri-{item.priority.lower()}">'
            f"<td>{idx}</td>"
            f'<td>{risk_emoji(item.priority)} {item.priority}</td>'
            f"<td>{item.score}</td>"
            f"<td>{hescape(mod)}</td>"
            f'<td class="file">{file_link}</td>'
            f"<td>{hescape(','.join(str(x) for x in item.match_lines[:8]))}</td>"
            f"<td>{hescape(', '.join(item.reasons))}</td>"
            f"</tr>\n"
        )

    truncation_warning = ""
    if truncated_count > 0:
        truncation_warning = f"""\
<div class="trunc-warn">
  <h3>⚠️ TRUNCATED — {truncated_count} LOW/BACKGROUND candidate(s) hidden</h3>
  <p>The table above shows <strong>ALL {total_high_med} HIGH/MEDIUM</strong> candidates.
     <strong>{truncated_count} additional LOW/BACKGROUND</strong> candidates were truncated for readability.</p>
  <p>To see all candidates, re-run with <code>--max-candidates {display_limit + truncated_count}</code>
     or check <code>impact-scan.json</code> for the complete list.</p>
  <p><em>Decision: Do you need these truncated candidates for your analysis? If the HIGH candidates
     already cover the blast radius, the truncated ones are low-risk. Re-run with a higher limit
     if you need full coverage.</em></p>
</div>"""

    tree_lines = []
    source_mod = extract_module(target.get("definition_file", ""), search_root) if search_root and target.get("definition_file") else ""
    root_label = f"{source_mod} (source)" if source_mod else (target.get("owner_class") or "Source")
    tree_lines.append(root_label)
    for i, (mod_name, m) in enumerate(sorted_mods):
        prefix = " └── " if i == len(sorted_mods) - 1 else " ├── "
        emoji = "🔴" if m["high"] > 0 else "⚫"
        tree_lines.append(f"{prefix}{emoji} {mod_name} ({m['files']} files, {m['high']} HIGH)")

    gate_html = '<span class="gate-pass">✅ PASS</span>' if gate["status"] == "PASS" else '<span class="gate-refine">⛔ REFINE_REQUIRED</span>'
    refine_block = ""
    if gate["status"] == "REFINE_REQUIRED":
        refine_block = '<div class="warn-box"><h3>⛔ REFINE REQUIRED</h3><p>Do not proceed. Narrow scope and re-run.</p></div>'

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Legacy Impact Audit — {hescape(target['symbol'])}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f8f9fa; color: #333; }}
  h1 {{ color: #1a1a2e; border-bottom: 2px solid #4361ee; padding-bottom: 8px; }}
  h2 {{ color: #2d3436; margin-top: 30px; }}
  .meta {{ color: #666; font-size: 14px; }}
  .gate-pass {{ background: #d4edda; color: #155724; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
  .gate-refine {{ background: #f8d7da; color: #721c24; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th {{ background: #4361ee; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #e9ecef; font-size: 13px; }}
  tr:hover {{ background: #f1f3ff; }}
  .file {{ font-family: monospace; font-size: 12px; max-width: 400px; word-break: break-all; }}
  tr.pri-high {{ background: #fff5f5; }}
  .tree {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 15px; border-radius: 6px; white-space: pre; line-height: 1.6; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 15px 0; }}
  .stat {{ background: white; padding: 12px; border-radius: 6px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .stat-val {{ font-size: 24px; font-weight: bold; color: #4361ee; }}
  .stat-label {{ font-size: 11px; color: #666; text-transform: uppercase; }}
  .warn-box {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 6px; margin: 20px 0; }}
  .warn-box h3 {{ margin-top: 0; }}
  .confirm-box {{ background: #cce5ff; border: 2px solid #004085; padding: 20px; border-radius: 8px; margin: 25px 0; }}
  .confirm-box h2 {{ margin-top: 0; color: #004085; border: none; }}
  .confirm-box ol {{ font-size: 15px; line-height: 1.8; }}
  .trunc-warn {{ background: #ffebee; border: 2px solid #d32f2f; padding: 20px; border-radius: 8px; margin: 25px 0; }}
  .trunc-warn h3 {{ margin-top: 0; color: #b71c1c; }} 
</style>
</head>
<body>

<h1>🔍 Legacy Impact Audit Report</h1>
<p class="meta">Generated: {payload['generated_at']} | Symbol: <strong>{hescape(target['symbol'])}</strong></p>

<h2>Target</h2>
<table>
<tr><th>Symbol</th><td><code>{hescape(target['symbol'])}</code></td></tr>
<tr><th>Owner Class</th><td><code>{hescape(target.get('owner_class', '') or '—')}</code></td></tr>
<tr><th>Owner Package</th><td><code>{hescape(target.get('owner_package', '') or '—')}</code></td></tr>
<tr><th>Definition File</th><td class="file">{hescape(target.get('definition_file', '') or '—')}</td></tr>
</table>

<h2>Gate</h2>
{gate_html}
<p><strong>Reasons:</strong> {', '.join(gate['reasons'])}</p>

<div class="stats">
  <div class="stat"><div class="stat-val">{payload['counts']['raw_matches']}</div><div class="stat-label">Raw Matches</div></div>
  <div class="stat"><div class="stat-val">{payload['counts']['filtered_matches']}</div><div class="stat-label">Filtered</div></div>
  <div class="stat"><div class="stat-val">{payload['counts']['candidate_files']}</div><div class="stat-label">Candidate Files</div></div>
  <div class="stat"><div class="stat-val">{payload['counts']['reported_candidates']}</div><div class="stat-label">Reported</div></div>
</div>

<h2>Blast Radius</h2>
<p><strong>{len(modules)} module(s)</strong> affected.</p>
<div class="tree">{chr(10).join(str(line) for line in tree_lines if line is not None)}</div>

<h3>Module Summary</h3>
<table>
<tr><th>Module</th><th>Files</th><th>HIGH</th><th>Risk</th></tr>
{module_rows}
</table>

<h2>Ranked Candidates</h2>
<table>
<tr><th>#</th><th>Risk</th><th>Score</th><th>Module</th><th>File</th><th>Lines</th><th>Reasons</th></tr>
{candidate_rows}
</table>

{truncation_warning}

{refine_block}

<div class="confirm-box">
<h2>⚠️ CONFIRMATION GATE</h2>
<p><strong>You must review the audit results above before proceeding.</strong></p>
<ol>
  <li>Review the <strong>Blast Radius</strong> — which modules are impacted?</li>
  <li>Check <strong>Ranked Candidates</strong> — are all HIGH entries confirmed?</li>
  <li>Identify <strong>Regression Scope</strong>: which modules need testing?</li>
  <li>Decide <strong>L1 vs L2</strong>: does this API cross a public service boundary?</li>
  <li><strong>Confirm</strong> to proceed. If unsure, narrow and re-run.</li>
</ol>
<p><em>This gate exists to prevent unverified changes to legacy code. Do not bypass.</em></p>
</div>

<h2>Artifacts</h2>
<ul>
  <li>📄 <code>impact-report.md</code> — Markdown report</li>
  <li>🤖 <code>llm-packet.md</code> — LLM confirmation prompt</li>
  <li>📊 <code>impact-scan.json</code> — Machine-readable data</li>
</ul>

</body>
</html>"""
    path.write_text(html, encoding="utf-8")


def scan(args: argparse.Namespace) -> int:
    validate_encoding(args.encoding)
    repo_root = Path(args.root).resolve()
    search_root = repo_root
    if args.module_path:
        search_root = (repo_root / args.module_path).resolve()
    if args.output_dir == "__AUTO__":
        output_dir = default_output_dir(repo_root)
    elif not Path(args.output_dir).is_absolute():
        output_dir = repo_root / args.output_dir
    else:
        output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    include_globs = args.include_glob or DEFAULT_INCLUDE_GLOBS
    exclude_globs = DEFAULT_EXCLUDE_GLOBS + (args.exclude_glob or [])
    raw_matches = run_search(search_root, args.symbol, include_globs, exclude_globs, args.encoding)
    filtered_matches = [match for match in raw_matches if not is_noise_line(match.line)]
    definition_abs = resolve_path(args.definition_file, repo_root, search_root)
    candidates = rank_candidates(
        search_root=search_root,
        matches=filtered_matches,
        symbol=args.symbol,
        owner_class=args.owner_class,
        owner_package=args.owner_package,
        definition_abs=definition_abs,
        context_lines=args.context_lines,
        source_encoding=args.encoding,
    )
    top_candidates = candidates[: args.max_candidates]
    status, reasons = gate_status(
        symbol=args.symbol,
        raw_count=len(raw_matches),
        filtered_count=len(filtered_matches),
        owner_class=args.owner_class,
        owner_package=args.owner_package,
        raw_limit=args.raw_limit,
        generic_limit=args.generic_limit,
    )
    cache_file = Path(args.cache_file)
    if not cache_file.is_absolute():
        cache_file = repo_root / cache_file
    cache_key = compute_cache_key(
        repo_root=repo_root,
        symbol=args.symbol,
        owner_class=args.owner_class,
        owner_package=args.owner_package,
        definition_file=args.definition_file,
        definition_abs=definition_abs,
        candidates=top_candidates,
        source_encoding=args.encoding,
    )
    cache = load_cache(cache_file)
    cache_status = "hit" if cache.get("entries", {}).get(cache_key) else "miss"
    payload = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": {
            "symbol": args.symbol,
            "owner_class": args.owner_class,
            "owner_package": args.owner_package,
            "definition_file": args.definition_file,
            "definition_file_resolved": str(definition_abs) if definition_abs else None,
            "root": str(repo_root),
            "search_root": str(search_root),
            "module_path": args.module_path,
            "encoding": args.encoding,
        },
        "gate": {"status": status, "reasons": reasons},
        "counts": {
            "raw_matches": len(raw_matches),
            "filtered_matches": len(filtered_matches),
            "candidate_files": len(candidates),
            "reported_candidates": len(top_candidates),
        },
        "cache": {"file": str(cache_file), "key": cache_key, "status": cache_status},
        "candidates": [candidate_to_dict(item) for item in candidates],
    }

    scan_json = output_dir / "impact-scan.json"
    report_md = output_dir / "impact-report.md"
    report_html = output_dir / "impact-report.html"
    packet_md = output_dir / "llm-packet.md"
    write_json(scan_json, payload)
    write_report(report_md, payload, top_candidates, search_root)
    write_html_report(report_html, payload, top_candidates, candidates, search_root)
    write_llm_packet(packet_md, payload, top_candidates)

    print(f"gate={status}")
    print(f"raw_matches={len(raw_matches)} filtered_matches={len(filtered_matches)} candidate_files={len(candidates)}")
    print(f"cache={cache_status} key={cache_key}")
    print(f"report={report_md}")
    print(f"html={report_html}")
    print(f"packet={packet_md}")
    print(f"json={scan_json}")
    if status == "REFINE_REQUIRED" and args.fail_on_refine:
        return 2
    return 0


def cache_put(args: argparse.Namespace) -> int:
    cache_file = Path(args.cache_file)
    cache = load_cache(cache_file)
    entries = cache.setdefault("entries", {})
    verdict_text = read_text(Path(args.verdict_file)) if args.verdict_file else sys.stdin.read()
    entries[args.key] = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": args.target or "",
        "confidence": args.confidence,
        "verdict": verdict_text,
    }
    removed = prune_cache(cache, args.cache_max_entries, args.cache_ttl_days)
    write_json(cache_file, cache)
    print(f"stored cache entry {args.key} in {cache_file}")
    if removed:
        print(f"pruned {removed} old cache entries")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legacy impact audit funnel")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_parser = sub.add_parser("scan", help="Run rg retrieval, ranking, report, and LLM packet generation")
    scan_parser.add_argument("--root", default=".", help="Repository root")
    scan_parser.add_argument("--module-path", default=None, help="Optional module path under root to narrow search")
    scan_parser.add_argument("--symbol", required=True, help="Method or symbol name to search")
    scan_parser.add_argument("--owner-class", default=None, help="Class that owns the method")
    scan_parser.add_argument("--owner-package", default=None, help="Package of the owner class")
    scan_parser.add_argument("--definition-file", default=None, help="Path to the file defining the target method")
    scan_parser.add_argument("--output-dir", default="__AUTO__", help="Output directory (default: LEGACY_IMPACT_RESULTS/YYYYMMDD-NN/)")
    scan_parser.add_argument("--cache-file", default=".ai/legacy-impact-audit/cache.json", help="Dependency verdict cache")
    scan_parser.add_argument("--max-candidates", type=int, default=100, help="Max candidates in report (HIGH never truncated)")
    scan_parser.add_argument("--context-lines", type=int, default=6, help="Context lines around each match")
    scan_parser.add_argument("--raw-limit", type=int, default=1000, help="Hard raw-match breaker")
    scan_parser.add_argument("--generic-limit", type=int, default=200, help="Breaker for generic symbols without owner info")
    scan_parser.add_argument(
        "--encoding",
        default=DEFAULT_ENCODING,
        help="Source file encoding for rg and snippet extraction; use 'auto' to let rg use its default detection",
    )
    scan_parser.add_argument("--include-glob", action="append", help="Override include glob; repeatable")
    scan_parser.add_argument("--exclude-glob", action="append", help="Additional rg exclude glob; repeatable")
    scan_parser.add_argument("--fail-on-refine", action="store_true", help="Exit 2 when gate is REFINE_REQUIRED")
    scan_parser.set_defaults(func=scan)

    cache_parser = sub.add_parser("cache-put", help="Store an LLM-confirmed verdict under a scan cache key")
    cache_parser.add_argument("--cache-file", default=".ai/legacy-impact-audit/cache.json")
    cache_parser.add_argument("--key", required=True)
    cache_parser.add_argument("--target", default=None)
    cache_parser.add_argument("--confidence", choices=["high", "medium", "low"], default="medium")
    cache_parser.add_argument("--verdict-file", default=None, help="Markdown/JSON verdict file; stdin if omitted")
    cache_parser.add_argument("--cache-max-entries", type=int, default=500, help="Maximum cache entries to retain; 0 disables")
    cache_parser.add_argument("--cache-ttl-days", type=int, default=0, help="Prune entries older than this many days; 0 disables")
    cache_parser.set_defaults(func=cache_put)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
