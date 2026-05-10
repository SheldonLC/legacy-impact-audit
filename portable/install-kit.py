#!/usr/bin/env python3
"""Install legacy-impact-audit for multiple coding agents."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


SKILL_NAME = "legacy-impact-audit"
MARKER_START = "<!-- legacy-impact-audit:start -->"
MARKER_END = "<!-- legacy-impact-audit:end -->"


USER_SKILL_DIRS = {
    "codex": lambda home: Path(os.environ.get("CODEX_HOME", home / ".codex")) / "skills",
    "claude": lambda home: home / ".claude" / "skills",
    "opencode": lambda home: home / ".config" / "opencode" / "skills",
    "copilot": lambda home: home / ".copilot" / "skills",
    "deepcode": lambda home: home / ".agents" / "skills",
}

PROJECT_SKILL_DIRS = {
    "claude": lambda root: root / ".claude" / "skills",
    "opencode": lambda root: root / ".opencode" / "skills",
    "copilot": lambda root: root / ".github" / "skills",
    "deepcode": lambda root: root / ".deepcode" / "skills",
}


def copy_skill(source: Path, destination_parent: Path, force: bool) -> Path:
    destination = destination_parent / SKILL_NAME
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".DS_Store")
    if source.resolve() == destination.resolve():
        return destination
    if destination.exists():
        if not force:
            raise SystemExit(f"Destination exists: {destination}. Re-run with --force to overwrite.")
        shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=ignore)
    return destination


def append_marked_block(path: Path, block: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    if MARKER_START in existing and MARKER_END in existing:
        before = existing.split(MARKER_START, 1)[0].rstrip()
        after = existing.split(MARKER_END, 1)[1].lstrip()
        content = f"{before}\n\n{block.strip()}\n\n{after}".strip() + "\n"
    else:
        content = (existing.rstrip() + "\n\n" + block.strip() + "\n").lstrip()
    path.write_text(content, encoding="utf-8")


def instruction_block(script_path: str) -> str:
    return f"""\
{MARKER_START}
## Legacy Impact Audit

Before planning or implementing risky legacy Java changes, run a legacy impact audit.

Mandatory triggers:
- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, workflow, or other core business logic

Gate rules:
- Run impact audit before finalizing the implementation plan.
- Run it again after code changes and before functional test case design or code review.
- Do not proceed if the audit returns `REFINE_REQUIRED`; narrow by owner class, package, module, or definition file first.
- Do not ask an LLM to analyze broad raw search results; use the generated audit report and packet.
- Test scope and regression scope must be derived from confirmed `real_dependency` and `possible_dependency` candidates.

Command pattern:

```bash
python3 "{script_path}" scan \\
  --root . \\
  --symbol METHOD_NAME \\
  --owner-class OWNER_CLASS \\
  --owner-package OWNER_PACKAGE \\
  --definition-file path/to/OwnerClass.java
```
{MARKER_END}
"""


def install_gemini(source: Path, home: Path, scope: str, project_root: Path, force: bool) -> list[Path]:
    installed: list[Path] = []
    if scope == "user":
        skill_dir = copy_skill(source, home / ".agents" / "skills", force)
        gemini_file = home / ".gemini" / "GEMINI.md"
        append_marked_block(gemini_file, instruction_block(str(skill_dir / "scripts" / "impact_audit.py")))
        installed.extend([skill_dir, gemini_file])
    else:
        skill_dir = copy_skill(source, project_root / ".ai" / "legacy-impact-audit" / "skills", force)
        gemini_file = project_root / "GEMINI.md"
        append_marked_block(gemini_file, instruction_block(str(skill_dir / "scripts" / "impact_audit.py")))
        installed.extend([skill_dir, gemini_file])
    return installed


def install_instruction_adapter(agent: str, source: Path, home: Path, scope: str, project_root: Path, force: bool) -> list[Path]:
    if agent == "gemini":
        return install_gemini(source, home, scope, project_root, force)

    if scope == "user":
        target_parent_factory = USER_SKILL_DIRS.get(agent)
        if not target_parent_factory:
            raise SystemExit(f"User-scope install is not defined for {agent}")
        return [copy_skill(source, target_parent_factory(home), force)]

    target_parent_factory = PROJECT_SKILL_DIRS.get(agent)
    if not target_parent_factory:
        raise SystemExit(f"Project-scope install is not defined for {agent}")
    installed = [copy_skill(source, target_parent_factory(project_root), force)]

    if agent == "opencode":
        append_marked_block(project_root / "AGENTS.md", instruction_block(str(installed[0] / "scripts" / "impact_audit.py")))
        installed.append(project_root / "AGENTS.md")
    elif agent == "copilot":
        append_marked_block(
            project_root / ".github" / "copilot-instructions.md",
            instruction_block(str(installed[0] / "scripts" / "impact_audit.py")),
        )
        installed.append(project_root / ".github" / "copilot-instructions.md")
    return installed


def parse_agents(raw: str) -> list[str]:
    if raw == "all":
        return ["codex", "claude", "opencode", "gemini", "copilot", "deepcode"]
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Install legacy-impact-audit")
    parser.add_argument(
        "--agent",
        default="codex",
        help="Agent target: codex, claude, opencode, gemini, copilot, deepcode, all, or comma-separated list",
    )
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--project-root", default=".", help="Project root for project-scope installs")
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="Backward-compatible override for Codex destination skills directory",
    )
    parser.add_argument(
        "--source",
        default=str(Path(__file__).resolve().parents[1] / SKILL_NAME),
        help="Source skill directory",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing installed skill")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    home = Path.home()
    project_root = Path(args.project_root).resolve()
    if not (source / "SKILL.md").exists():
        raise SystemExit(f"Source skill not found: {source}")

    installed: list[Path] = []
    for agent in parse_agents(args.agent):
        if agent == "codex" and args.skills_dir:
            if args.scope != "user":
                raise SystemExit("--skills-dir is only valid with --scope user")
            installed.append(copy_skill(source, Path(args.skills_dir).expanduser().resolve(), args.force))
            continue
        installed.extend(install_instruction_adapter(agent, source, home, args.scope, project_root, args.force))

    for path in installed:
        print(f"Installed/updated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
