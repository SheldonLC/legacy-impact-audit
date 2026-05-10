# Install For opencode

opencode supports Agent Skills from configured skill directories. For project-level enforcement, also install an `AGENTS.md` instruction block.

## User Install

```bash
python3 portable/install-kit.py --agent opencode --scope user --force
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

Project install writes:

```text
/path/to/target/repo/.opencode/skills/legacy-impact-audit
/path/to/target/repo/AGENTS.md
```

The `AGENTS.md` block is idempotent and marked with `legacy-impact-audit` comments.

## Source

opencode skills documentation: <https://opencode.ai/docs/skills>
