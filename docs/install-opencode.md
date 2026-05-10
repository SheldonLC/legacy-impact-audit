# Install For opencode

opencode supports Agent Skills from configured skill directories. For project-level enforcement, also install an `AGENTS.md` instruction block.

## User Install

```bash
python3 portable/install-kit.py --agent opencode --scope user --force
```

No-Python install:

```bash
sh portable/install-kit.sh --agent opencode --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent opencode -Scope user -Force
```

Default destination:

```text
~/.config/opencode/skills/legacy-impact-audit
```

## Project Install

```bash
python3 portable/install-kit.py \
  --agent opencode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

No-Python project install:

```bash
sh portable/install-kit.sh \
  --agent opencode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Project install writes:

```text
/path/to/target/repo/.opencode/skills/legacy-impact-audit
/path/to/target/repo/AGENTS.md
```

The `AGENTS.md` block is idempotent and marked with `legacy-impact-audit` comments.

Running the audit scripts requires Python 3 and ripgrep.

## Source

opencode skills documentation: <https://opencode.ai/docs/skills>
