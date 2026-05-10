# Install For Deep Code

Deep Code supports Agent Skills in user and project skill folders. This repository can be installed as a native skill.

## User Install

```bash
python3 portable/install-kit.py --agent deepcode --scope user --force
```

No-Python install:

```bash
sh portable/install-kit.sh --agent deepcode --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent deepcode -Scope user -Force
```

Default destination:

```text
~/.agents/skills/legacy-impact-audit
```

## Project Install

```bash
python3 portable/install-kit.py \
  --agent deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

No-Python project install:

```bash
sh portable/install-kit.sh \
  --agent deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Project destination:

```text
/path/to/target/repo/.deepcode/skills/legacy-impact-audit
```

Running the audit scripts requires Python 3 and ripgrep.

## Source

Deep Code Agent Skills documentation: <https://api-docs.deepseek.com/quick_start/agent_integrations/deepcode>
