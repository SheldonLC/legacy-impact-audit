#!/usr/bin/env node
/**
 * Auto-install script for `npm install -g legacy-impact-audit`.
 * Runs via `postinstall` in package.json.
 *
 * Detects the current agent (opencode, codex, claude) and copies
 * the skill directory into the agent's global skill path.
 * Also writes an AGENTS.md instruction block for project scope.
 */

const fs = require("node:fs");
const path = require("node:path");

const SKILL_NAME = "legacy-impact-audit";
const MARKER_START = "<!-- legacy-impact-audit:start -->";
const MARKER_END = "<!-- legacy-impact-audit:end -->";

// Resolve package root (where this script lives relative to node_modules)
const PACKAGE_ROOT = path.resolve(__dirname);
const SKILL_SOURCE = path.join(PACKAGE_ROOT, SKILL_NAME);
const IS_NPM_GLOBAL = isNpmGlobal();

// Agent skill target directories (user scope)
const USER_TARGETS = [
  { name: "opencode", skillDir: path.join(osHome(), ".config", "opencode", "skills", SKILL_NAME) },
  { name: "codex", skillDir: path.join(
      process.env.CODEX_HOME ? process.env.CODEX_HOME : path.join(osHome(), ".codex"),
      "skills", SKILL_NAME
    ),
  },
  { name: "claude", skillDir: path.join(osHome(), ".claude", "skills", SKILL_NAME) },
];

function osHome() {
  return process.env.HOME || process.env.USERPROFILE || ".";
}

function isNpmGlobal() {
  // Detect if this is a global npm install by checking if we're in npm's global node_modules
  try {
    const globalPrefix = path.resolve(npmRootGlobal());
    const ourPath = path.resolve(__dirname);
    return ourPath.startsWith(globalPrefix);
  } catch {
    return false;
  }
}

function npmRootGlobal() {
  // Run: npm root -g
  const { execSync } = require("child_process");
  try {
    return execSync("npm root -g", { encoding: "utf-8", timeout: 5000 }).trim();
  } catch {
    return process.platform === "win32"
      ? path.join(process.env.APPDATA || osHome(), "..", "node_modules")
      : "/usr/local/lib/node_modules";
  }
}

function copyRecursive(src, dest) {
  if (!fs.existsSync(src)) return false;
  const entries = fs.readdirSync(src, { withFileTypes: true });
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.name === "__pycache__" || entry.name === ".git" || entry.name === ".DS_Store" || entry.name.endsWith(".pyc")) {
      continue;
    }
    if (entry.isDirectory()) {
      copyRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
  return true;
}

function detectAgent() {
  if (fs.existsSync(path.join(osHome(), ".config", "opencode"))) return "opencode";
  if (fs.existsSync(path.join(osHome(), ".codex"))) return "codex";
  if (fs.existsSync(path.join(osHome(), ".claude"))) return "claude";
  return "opencode"; // default
}

function instructionBlock(scriptPath) {
  const escaped = scriptPath.replace(/\\/g, "/");
  return `\
${MARKER_START}
## Legacy Impact Audit

Before planning or implementing risky legacy Java changes, run a legacy impact audit.

Mandatory triggers:
- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, workflow, or other core business logic

Gate rules:
- Run impact audit before finalizing the implementation plan.
- Run it again after code changes and before functional test case design or code review.
- Do not proceed if the audit returns \`REFINE_REQUIRED\`; narrow by owner class, package, module, or definition file first.
- Do not ask an LLM to analyze broad raw search results; use the generated audit report and packet.
- Test scope and regression scope must be derived from confirmed \`real_dependency\` and \`possible_dependency\` candidates.

Command pattern:

\`\`\`bash
python3 "${escaped}/scripts/impact_audit.py" scan \\
  --root . \\
  --symbol METHOD_NAME \\
  --owner-class OWNER_CLASS \\
  --owner-package OWNER_PACKAGE \\
  --definition-file path/to/OwnerClass.java
\`\`\`
${MARKER_END}`;
}

function writeMarkedBlock(filePath, block) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
  let existing = "";
  if (fs.existsSync(filePath)) {
    existing = fs.readFileSync(filePath, "utf-8");
  }
  const startIdx = existing.indexOf(MARKER_START);
  const endIdx = existing.indexOf(MARKER_END);
  let content;
  if (startIdx !== -1 && endIdx !== -1) {
    const before = existing.substring(0, startIdx).trimEnd();
    const after = existing.substring(endIdx + MARKER_END.length).trimStart();
    content = `${before}\n\n${block.trim()}\n\n${after}\n`;
  } else {
    content = `${existing.trimEnd()}\n\n${block.trim()}\n`;
  }
  fs.writeFileSync(filePath, content, "utf-8");
}

function main() {
  // Only auto-install during global install, not local project install
  if (!IS_NPM_GLOBAL) {
    console.log("[legacy-impact-audit] Skipping auto-install: not a global install.");
    console.log("[legacy-impact-audit] Run `legacy-impact-audit install` to install the skill.");
    return;
  }

  if (!fs.existsSync(SKILL_SOURCE)) {
    console.error(`[legacy-impact-audit] ERROR: Skill source not found at ${SKILL_SOURCE}`);
    process.exit(1);
  }

  // Detect active agent(s) and install
  const found = USER_TARGETS.filter(t => {
    // Check if the agent config dir exists on this machine
    const parent = path.dirname(t.skillDir);
    return fs.existsSync(path.dirname(parent)) || // ~/.config/opencode exists
           fs.existsSync(parent);                   // ~/.config/opencode/skills exists
  });

  if (found.length === 0) {
    // No known agent found — try default (opencode)
    const target = USER_TARGETS.find(t => t.name === "opencode");
    if (target) {
      fs.mkdirSync(path.dirname(target.skillDir), { recursive: true });
      copyRecursive(SKILL_SOURCE, target.skillDir);
      console.log(`[legacy-impact-audit] Installed to ${target.skillDir}`);
    }
    return;
  }

  for (const target of found) {
    const parent = path.dirname(target.skillDir);
    fs.mkdirSync(parent, { recursive: true });
    copyRecursive(SKILL_SOURCE, target.skillDir);
    console.log(`[legacy-impact-audit] Installed for ${target.name}: ${target.skillDir}`);
  }

  console.log("[legacy-impact-audit] Prerequisites: python (or python3) and ripgrep (rg) must be in PATH.");
  console.log("[legacy-impact-audit] For project scope: `legacy-impact-audit install --project ./repo`.");
}

main();
