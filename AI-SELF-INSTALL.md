# AI Self-Install Guide

This file is written for an AI coding agent. If a user asks you to install `legacy-impact-audit`, do not ask the user to run the commands unless you are blocked by permissions, missing tools, or authentication. Execute the steps yourself.

## Goal

Install `legacy-impact-audit` for the current agent or for the target project, validate the installation, and report exactly what was installed.

## Rules

- Do not modify unrelated repository files.
- Do not install hooks unless the user explicitly asks for hook enforcement.
- Do not call an LLM from installation scripts. The scripts are deterministic.
- Prefer project-scope install when the user wants a repository to enforce the audit gate for multiple agents.
- Prefer user-scope install when the user wants the current machine/account to use the skill globally.

## Step 1: Locate The Kit

You are usually reading this file from the kit root. Confirm these files exist:

```bash
test -f legacy-impact-audit/SKILL.md
test -f legacy-impact-audit/scripts/impact_audit.py
test -f legacy-impact-audit/scripts/validate_impact_audit.py
test -f portable/install-kit.py
```

If the files are missing, stop and report that the repository is not a valid `legacy-impact-audit` kit.

## Step 2: Detect Target Agent

If the user named an agent, use it:

- `codex`
- `claude`
- `opencode`
- `gemini`
- `copilot`
- `deepcode`
- `all`

If the user did not name an agent, infer from the current environment:

- Codex: install `--agent codex`
- Claude Code: install `--agent claude`
- opencode: install `--agent opencode`
- Gemini CLI: install `--agent gemini`
- GitHub Copilot coding agent: install `--agent copilot`
- Deep Code: install `--agent deepcode`

If unsure and the user wants broad availability, use `--agent all`.

## Step 3: Choose Scope

Use user scope for global local usage:

```bash
python3 portable/install-kit.py --agent AGENT --scope user --force
```

Use project scope when installing into a target repository:

```bash
python3 portable/install-kit.py \
  --agent AGENT \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

For all supported user-level targets:

```bash
python3 portable/install-kit.py --agent all --scope user --force
```

For common project adapters:

```bash
python3 portable/install-kit.py \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

## Step 4: Validate

Run Python syntax checks:

```bash
python3 -m py_compile \
  legacy-impact-audit/scripts/impact_audit.py \
  legacy-impact-audit/scripts/validate_impact_audit.py \
  portable/install-kit.py
```

For Codex installs, validate the skill if the validator exists:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  "${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit"
```

If the validator path does not exist, skip it and say so.

## Step 5: Smoke Test

Run a deterministic scan against the kit itself:

```bash
python3 legacy-impact-audit/scripts/impact_audit.py scan \
  --root legacy-impact-audit \
  --symbol scan \
  --include-glob '*.py' \
  --max-candidates 5 \
  --output-dir /tmp/legacy-impact-audit-self-test
```

Validate the generated artifacts:

```bash
python3 legacy-impact-audit/scripts/validate_impact_audit.py \
  --root . \
  --audit-dir /tmp/legacy-impact-audit-self-test \
  --mode worktree \
  --always-require
```

## Step 6: Report

Report:

- Agent target installed.
- Scope used.
- Paths created or updated.
- Validation commands run.
- Any skipped validation and why.
- Whether hooks were installed. Default should be no.

## Optional Hook Install

Only if the user explicitly asks for hook enforcement:

```bash
cp legacy-impact-audit/scripts/precommit-impact-reminder.sh /path/to/target/repo/.git/hooks/pre-commit
chmod +x /path/to/target/repo/.git/hooks/pre-commit
```

Then run:

```bash
python3 legacy-impact-audit/scripts/validate_impact_audit.py \
  --root /path/to/target/repo \
  --mode staged
```
