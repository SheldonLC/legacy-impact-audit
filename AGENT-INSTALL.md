# Agent Install Guide: legacy-impact-audit

This guide is for another coding agent installing `legacy-impact-audit` from this portable kit.

For fully self-directed installation where the agent should run commands itself, read [AI-SELF-INSTALL.md](AI-SELF-INSTALL.md).

## What This Installs

`legacy-impact-audit` is a low-token impact audit skill/adapter for legacy Java or mixed enterprise repositories. It uses a three-layer funnel:

- `rg` retrieval for cheap full-workspace search.
- Python heuristic ranking to reduce candidates.
- LLM semantic confirmation only on the generated small candidate packet.

It does not require MCP servers or repository-specific knowledge graphs.

Supported install targets:

- Codex
- Claude Code
- opencode
- Gemini CLI
- GitHub Copilot
- Deep Code

For Codex, installation means the skill directory plus `~/.codex/AGENTS.md`. This kit does not require a Codex startup hook.

## Prerequisites

- Installation: Python is optional. Use `portable/install-kit.py`, `portable/install-kit.sh`, `portable/install-kit.ps1`, or manual copy.
- Audit execution: `python3` must be available in PATH.
- Search: `rg` / ripgrep must be available in PATH. Run `rg --version` before the first audit and stop with install guidance if it is missing.
- A writable Codex skills directory, normally `$CODEX_HOME/skills` or `~/.codex/skills`.

## Install

From the extracted kit root, install for Codex with the Python installer:

```bash
python3 portable/install-kit.py --agent codex --scope user --force
```

Install for Codex without Python:

```bash
sh portable/install-kit.sh --agent codex --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -Scope user -Force
```

Install for every supported user-level target:

```bash
python3 portable/install-kit.py --agent all --scope user --force
```

No-Python equivalents:

```bash
sh portable/install-kit.sh --agent all --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent all -Scope user -Force
```

To install Codex into an explicit skills directory:

```bash
python3 portable/install-kit.py --agent codex --skills-dir "$HOME/.codex/skills" --force
```

Expected result:

```text
Installed legacy-impact-audit to .../skills/legacy-impact-audit
```

Project adapters can be installed with:

```bash
python3 portable/install-kit.py \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Per-agent instructions live in `docs/`.

If Python is unavailable, read [NO-PYTHON-INSTALL.md](NO-PYTHON-INSTALL.md). Installation can complete, but smoke tests and gate validation must be skipped until Python 3 is available.

## Validate

Check that the skill exists:

```bash
test -f "$HOME/.codex/skills/legacy-impact-audit/SKILL.md"
test -f "$HOME/.codex/skills/legacy-impact-audit/scripts/impact_audit.py"
test -f "$HOME/.codex/skills/legacy-impact-audit/scripts/validate_impact_audit.py"
```

If the Codex skill validator is available, run:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  "$HOME/.codex/skills/legacy-impact-audit"
```

## Smoke Test

From any repository or temporary directory:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/impact_audit.py" scan \
  --root . \
  --symbol execute \
  --max-candidates 5 \
  --raw-limit 50 \
  --generic-limit 5
```

If the symbol is too generic, `REFINE_REQUIRED` is a valid result. It means the gate is working and the agent must re-run with `--owner-class`, `--owner-package`, `--module-path`, or `--definition-file`.

## Use On A Java Method

Run from the target repository root:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/impact_audit.py" scan \
  --root . \
  --symbol METHOD_NAME \
  --owner-class OWNER_CLASS \
  --owner-package OWNER_PACKAGE \
  --definition-file path/to/OwnerClass.java \
  --encoding utf-8
```

For legacy files that are not UTF-8, pass the appropriate encoding, such as `--encoding gbk`, or use `--encoding auto` to let ripgrep use its default detection.

Read these outputs:

```text
.ai/legacy-impact-audit/impact-report.md
.ai/legacy-impact-audit/llm-packet.md
.ai/legacy-impact-audit/impact-scan.json
```

The agent should only call the LLM after reading `llm-packet.md`. Do not ask the LLM to analyze raw `rg` results.

## Validate Gate Artifacts

This section is about repository Git hooks or CI validation, not a Codex startup hook.

Use this in hooks or CI after an audit has been generated:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/validate_impact_audit.py" \
  --root . \
  --mode staged \
  --max-age-minutes 240
```

## Optional Hook

Do not install hooks automatically unless the user asks. If requested, copy:

```text
legacy-impact-audit/scripts/precommit-impact-reminder.sh
```

to:

```text
.git/hooks/pre-commit
```

Then make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

The hook validates local audit artifacts; it does not call an LLM.
