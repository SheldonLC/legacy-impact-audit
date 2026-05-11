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
    # SessionStart payloads are optional for this hook. We do not need any
    # fields from stdin to produce the reminder context, so empty or invalid
    # stdin should not block the Codex session.
    try:
        raw = sys.stdin.read()
        if raw.strip():
            json.loads(raw)
    except (json.JSONDecodeError, OSError):
        pass

    # Find the skill directory (relative to this script's location)
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    context = f"""\
## Legacy Impact Audit (MANDATORY — DO NOT BYPASS)

You MUST run an impact audit for ANY code change. No exceptions.
Adding a method, changing a signature, modifying ANY file = MUST RUN.

The ONLY skip: pure read (query, search, explain), debug without changes.
If you think "this doesn't need an audit" — STOP. Run it anyway.
Adding an overloaded method IS a public API change.

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
