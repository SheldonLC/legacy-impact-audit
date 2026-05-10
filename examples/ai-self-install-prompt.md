# AI Self-Install Prompt

Give this prompt to another coding agent when you want it to install `legacy-impact-audit` by itself.

```text
Read `AI-SELF-INSTALL.md` in this repository and install `legacy-impact-audit`.

Do not ask me to run install commands unless you are blocked by permissions or missing tools. Detect the agent target if possible; if unsure, install for all supported user-level agents. Run the validation and smoke-test steps in the guide. Do not install git hooks unless I explicitly ask for hook enforcement.

After installing, report the installed paths, validation results, and any skipped steps.
```
