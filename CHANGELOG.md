# Changelog

## 0.2.3

- Add Python-free installers: `portable/install-kit.sh` and `portable/install-kit.ps1`.
- Add `NO-PYTHON-INSTALL.md` for manual and script-based installation without Python.
- Add `sensitive-scan-gate.sh` for local `pre-commit`, `commit-msg`, and `pre-push` blocking with untracked private patterns.
- Clarify that Python is optional for installation but still required for deterministic audit execution and gate validation.
- Add CI smoke coverage for the shell installer.

## 0.2.2

- Add a mock legacy Java project under `examples/mock-legacy-java`.
- Add `docs/workflow-test-guide.md` and `examples/workflow-test-prompt.md` for cross-agent workflow validation.
- Extend CI to run the mock workflow fixture, including L1 audit, generic-method `REFINE_REQUIRED`, and validator checks.

## 0.2.1

- Add `AI-SELF-INSTALL.md` for agents that should read, install, validate, and report without asking the user to run install commands.
- Add `examples/ai-self-install-prompt.md` as a copy-paste bootstrap prompt for other coding agents.

## 0.2.0

- Add multi-agent installation support for Codex, Claude Code, opencode, Gemini CLI, GitHub Copilot, and Deep Code.
- Add per-agent installation guides under `docs/`.
- Extend `portable/install-kit.py` with `--agent`, `--scope`, and `--project-root`.
- Add project instruction adapters for `AGENTS.md`, `GEMINI.md`, and `.github/copilot-instructions.md`.
- Add CI smoke coverage for multi-agent installer paths.

## 0.1.0

- Initial `legacy-impact-audit` Codex skill.
- Add deterministic `impact_audit.py` scanner and `validate_impact_audit.py` gate validator.
- Add portable kit, MIT license, and GitHub-ready repository structure.
