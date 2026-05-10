# Install For GitHub Copilot

GitHub Copilot coding agent supports skills in repository/user skill locations. For repository-level guidance, also use Copilot custom instructions.

## User Install

```bash
python3 portable/install-kit.py --agent copilot --scope user --force
```

No-Python install:

```bash
sh portable/install-kit.sh --agent copilot --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent copilot -Scope user -Force
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

No-Python project install:

```bash
sh portable/install-kit.sh \
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

Running the audit scripts requires Python 3 and ripgrep.

## Sources

GitHub Copilot skills documentation: <https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/create-skills>

GitHub Copilot custom instructions documentation: <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>
