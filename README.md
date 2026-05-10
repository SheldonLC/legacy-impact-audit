# legacy-impact-audit

`legacy-impact-audit` is a Codex skill and deterministic helper toolkit for low-token impact analysis in legacy Java or mixed enterprise repositories.

Current version: `0.2.4`

It is designed for repositories where full dependency graphs are unavailable, stale, too expensive to build, or unreliable for daily change work.

## What It Does

The workflow uses a cheap-to-expensive funnel:

1. Search with `rg` across source/config files.
2. Filter noise and rank candidate callers with deterministic Python heuristics.
3. Generate a small LLM packet for semantic confirmation.
4. Validate audit artifacts in hooks or CI before review/test planning.

The scripts do not call an LLM. The agent performs semantic confirmation only after the candidate set has been reduced.

## Repository Layout

```text
legacy-impact-audit/
  SKILL.md
  agents/openai.yaml
  scripts/impact_audit.py
  scripts/validate_impact_audit.py
  scripts/precommit-impact-reminder.sh
  scripts/sensitive-scan-gate.sh
  references/hook-patterns.md
  references/llm-verification-template.md
portable/
  install-kit.py
  install-kit.sh
  install-kit.ps1
  INSTALL-SAMPLES.md
docs/
  agent-install-matrix.md
  workflow-test-guide.md
  install-codex.md
  install-claude.md
  install-opencode.md
  install-gemini.md
  install-copilot.md
  install-deepcode.md
examples/
  AGENTS-impact-audit.md
  test-prompt.md
  workflow-test-prompt.md
  mock-legacy-java/
.github/workflows/ci.yml
AI-SELF-INSTALL.md
AGENT-INSTALL.md
NO-PYTHON-INSTALL.md
CHANGELOG.md
VERSION
```

## Install

Python is not required for installation. It is required later to run the deterministic audit scripts.

Install for Codex, the default target, with the Python installer:

```bash
python3 portable/install-kit.py --agent codex --scope user --force
```

Or install without Python:

```bash
sh portable/install-kit.sh --agent codex --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -Scope user -Force
```

This installs the skill to:

```text
${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit
```

Install for every supported user-level agent target:

```bash
python3 portable/install-kit.py --agent all --scope user --force
```

For full no-Python installation options, see [NO-PYTHON-INSTALL.md](NO-PYTHON-INSTALL.md).

For agent-readable installation steps, see [AGENT-INSTALL.md](AGENT-INSTALL.md).

For fully self-directed AI installation, give the agent [AI-SELF-INSTALL.md](AI-SELF-INSTALL.md) or the prompt in [examples/ai-self-install-prompt.md](examples/ai-self-install-prompt.md).

For per-agent installation details, see:

- [Codex](docs/install-codex.md)
- [Claude Code](docs/install-claude.md)
- [opencode](docs/install-opencode.md)
- [Gemini CLI](docs/install-gemini.md)
- [GitHub Copilot](docs/install-copilot.md)
- [Deep Code](docs/install-deepcode.md)
- [Agent install matrix](docs/agent-install-matrix.md)

## Quick Scan

Run from a target repository:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/impact_audit.py" scan \
  --root . \
  --module-path path/to/module \
  --symbol METHOD_NAME \
  --owner-class OWNER_CLASS \
  --owner-package com.example.package \
  --definition-file path/to/OwnerClass.java \
  --encoding utf-8
```

Outputs:

```text
.ai/legacy-impact-audit/impact-report.md
.ai/legacy-impact-audit/llm-packet.md
.ai/legacy-impact-audit/impact-scan.json
```

If the result is `REFINE_REQUIRED`, do not perform semantic analysis yet. Re-run with a narrower module, owner class, owner package, or definition file.

## Mandatory Gate Usage

For teams using this as a mandatory process gate:

1. Run impact audit before finalizing the implementation plan.
2. Run impact audit again after code changes and before functional test design or code review.
3. Derive functional and regression test scope from confirmed `real_dependency` and `possible_dependency` candidates.
4. Use `validate_impact_audit.py` in pre-commit, pre-push, or CI to block missing/stale/refine-required audit artifacts.

An `AGENTS.md` snippet is available in [examples/AGENTS-impact-audit.md](examples/AGENTS-impact-audit.md).

For local-only sensitive term blocking, use `legacy-impact-audit/scripts/sensitive-scan-gate.sh` with an untracked pattern file under `.git/hooks`. See [hook patterns](legacy-impact-audit/references/hook-patterns.md).

## Workflow Test Fixture

Use [docs/workflow-test-guide.md](docs/workflow-test-guide.md) and [examples/workflow-test-prompt.md](examples/workflow-test-prompt.md) to validate the full workflow with another AI agent. The mock project lives in [examples/mock-legacy-java](examples/mock-legacy-java).

## Validate In Hooks Or CI

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/validate_impact_audit.py" \
  --root . \
  --mode staged \
  --max-age-minutes 240
```

Modes:

- `staged`: validate staged source/config changes, useful for pre-commit.
- `worktree`: validate unstaged worktree changes.
- `all`: validate all changes against `HEAD`, useful for pre-push or CI.

For stricter review gates:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/validate_impact_audit.py" \
  --root . \
  --mode all \
  --require-verdicts
```

This requires `.ai/legacy-impact-audit/semantic-verdict.md` to exist.

## Requirements

- Installation: Python is optional. Use `portable/install-kit.py`, `portable/install-kit.sh`, `portable/install-kit.ps1`, or manual copy.
- Audit execution: Python 3.10 or newer is recommended.
- Search: `rg` / ripgrep must be available in PATH. Run `rg --version` before first use on a fresh machine.
- Git is required for validator diff modes.
- Mixed-encoding repositories can pass `--encoding`, for example `--encoding utf-8`, `--encoding gbk`, or `--encoding auto`.

## License

MIT. See [LICENSE](LICENSE).

## CI

The included GitHub Actions workflow runs smoke tests for Python and no-Python installers, compiles scripts, runs a scan, and validates generated artifacts.

## Publishing Notes

This repository is ready to publish as a GitHub project.
