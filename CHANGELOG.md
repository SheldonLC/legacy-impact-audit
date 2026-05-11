# Changelog

## 0.2.23

- Make the Codex SessionStart hook tolerant of empty or invalid stdin payloads.
- Prevent SessionStart hook failures from blocking Codex startup when the hook input is absent.

## 0.2.22

- Migrate deprecated Codex `codex_hooks = true` config to `hooks = true` during install.
- Keep Codex hook installation compatible with newer Codex feature naming.

## 0.2.21

- Exclude `portable/__pycache__` and `.pyc` files from the npm package.
- Keep the published tarball free of local Python cache artifacts.

## 0.2.20

- Fix npm CLI and postinstall Gemini skill paths to match the documented `.agents` and `.ai/legacy-impact-audit` layout.
- Remove duplicate project hook installation in the npm CLI.
- Make npm-generated Codex/session hook commands and install instructions use OS-aware Python command selection.
- Remove duplicate Codex session hook implementation from `install.js`.
- Fix stale README version display.

## 0.2.8

- Add copilot, deepcode, and gemini agent targets to npm install CLI and postinstall.
- Add instruction file support for all 6 agents (AGENTS.md, CLAUDE.md, GEMINI.md, etc.).
- Add `--hooks` flag to install pre-commit hook in project scope (opt-in).
- Graceful skip when `.git/hooks` doesn't exist.

## 0.2.7

- Add blast radius summary with ASCII tree diagram grouping candidates by module.
- Add risk indicators (🔴🟡⚪⚫) to priority columns and module summaries.
- Add module extraction helper for monorepo-aware impact reports.
- Add module-based grouping and sort-by-risk in the ranked candidate table.

## 0.2.6

- Fix agent detection in postinstall for codex and claude.
- Add npm version badge and one-liner install command to README.
- Simplify install documentation with npm-first approach.

## 0.2.5

- Add `postinstall` auto-install script for `npm install -g`.
- Add `legacy-impact-audit` CLI with `install`, `update`, `version`, `help` commands.
- Add `.npmignore` to exclude build artifacts from published package.

## 0.2.4

- Fix Windows subprocess decoding by forcing UTF-8 replacement decoding for `rg` and Git command output.
- Add `--encoding` to scan commands for legacy source files.
- Make `precommit-impact-reminder.sh` mtime checks portable across GNU, macOS, and Git Bash environments.
- Document `LEGACY_IMPACT_AUDIT_HOME` and `rg` preflight expectations.
- Add optional cache pruning controls to `cache-put`.

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
