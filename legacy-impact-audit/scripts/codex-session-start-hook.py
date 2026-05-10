#!/usr/bin/env python3
"""
Codex SessionStart hook — reminds the agent about legacy-impact-audit.

Reads JSON on stdin, outputs JSON on stdout. Injects additionalContext
that tells the agent to run the audit before touching legacy Java code.

Installed by legacy-impact-audit postinstall.
"""

import json
import sys
import os


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        print(json.dumps({"decision": "block", "reason": "Failed to read hook input"}))
        return 1

    # Find the skill directory (relative to this script's location)
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    context = f"""\
## Legacy Impact Audit (mandatory)

You have legacy-impact-audit installed. Before changing any of the following, run an impact audit first:

- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, or core business logic

Run: python3 "{skill_dir}/scripts/impact_audit.py" scan \\
  --root . \\
  --symbol METHOD_NAME \\
  --owner-class OWNER_CLASS \\
  --owner-package OWNER_PACKAGE \\
  --definition-file path/to/OwnerClass.java

Gate: Do not proceed if the audit returns REFINE_REQUIRED.
"""

    print(json.dumps({
        "decision": "proceed",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
