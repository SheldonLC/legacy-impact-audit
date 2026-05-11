# Install For Codex

Codex uses this repository as a native skill.

Codex does not require a `SessionStart` hook. Codex uses `~/.codex/AGENTS.md` plus the installed skill directory.

## User Install

```bash
python3 portable/install-kit.py --agent codex --scope user --force
```

No-Python install:

```bash
sh portable/install-kit.sh --agent codex --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -Scope user -Force
```

Default destination:

```text
${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit
```

## Validate

Validation and audit execution require Python 3.

```bash
test -f "${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit/SKILL.md"
test -f "${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit/scripts/impact_audit.py"
```

If the Codex skill validator is available:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  "${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit"
```

## Use

```text
Use $legacy-impact-audit to audit the impact of changing METHOD_NAME before editing.
```

Any hook guidance elsewhere in this repository refers to optional Git hooks / CI gates, not a Codex startup hook.
