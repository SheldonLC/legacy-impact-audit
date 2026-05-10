# Install For GitHub Copilot

GitHub Copilot coding agent supports skills in repository/user skill locations. For repository-level guidance, also use Copilot custom instructions.

## User Install

```bash
python3 portable/install-kit.py --agent copilot --scope user --force
```

Default destination:

```text
~/.copilot/skills/legacy-impact-audit
```

## Project Install

```bash
python3 portable/install-kit.py \
  --agent copilot \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Project install writes:

```text
/path/to/target/repo/.github/skills/legacy-impact-audit
/path/to/target/repo/.github/copilot-instructions.md
```

The instructions file makes impact audit a mandatory planning/review gate for risky legacy Java changes.

## Sources

GitHub Copilot skills documentation: <https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/create-skills>

GitHub Copilot custom instructions documentation: <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>
