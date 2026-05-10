# Install For Gemini CLI

Gemini CLI primarily uses context files such as `GEMINI.md`. This repository installs a project/user instruction adapter that points Gemini to the same deterministic scripts.

## User Install

```bash
python3 portable/install-kit.py --agent gemini --scope user --force
```

No-Python install:

```bash
sh portable/install-kit.sh --agent gemini --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent gemini -Scope user -Force
```

This writes:

```text
~/.agents/skills/legacy-impact-audit
~/.gemini/GEMINI.md
```

## Project Install

```bash
python3 portable/install-kit.py \
  --agent gemini \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

No-Python project install:

```bash
sh portable/install-kit.sh \
  --agent gemini \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

This writes:

```text
/path/to/target/repo/.ai/legacy-impact-audit/skills/legacy-impact-audit
/path/to/target/repo/GEMINI.md
```

The `GEMINI.md` block is idempotent and tells Gemini to run `impact_audit.py` before risky legacy Java changes.

Running the audit scripts requires Python 3 and ripgrep.

## Source

Gemini CLI repository and context-file documentation: <https://github.com/google-gemini/gemini-cli>
