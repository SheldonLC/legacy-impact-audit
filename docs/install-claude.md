# Install For Claude Code

Claude Code supports Agent Skills with `SKILL.md` in user or project skill folders.

## User Install

```bash
python3 portable/install-kit.py --agent claude --scope user --force
```

Default destination:

```text
~/.claude/skills/legacy-impact-audit
```

## Project Install

Run from this repository:

```bash
python3 portable/install-kit.py \
  --agent claude \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Project destination:

```text
/path/to/target/repo/.claude/skills/legacy-impact-audit
```

## Use

```text
Use $legacy-impact-audit to audit the impact of changing METHOD_NAME before editing.
```

## Source

Claude Code Agent Skills documentation: <https://docs.claude.com/en/docs/claude-code/skills>
