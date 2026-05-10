# Install For Deep Code

Deep Code supports Agent Skills in user and project skill folders. This repository can be installed as a native skill.

## User Install

```bash
python3 portable/install-kit.py --agent deepcode --scope user --force
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

Project destination:

```text
/path/to/target/repo/.deepcode/skills/legacy-impact-audit
```

## Source

Deep Code Agent Skills documentation: <https://api-docs.deepseek.com/quick_start/agent_integrations/deepcode>
