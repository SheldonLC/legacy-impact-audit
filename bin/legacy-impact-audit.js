#!/usr/bin/env node
/**
 * legacy-impact-audit CLI — Install the skill for OpenCode, Codex, or Claude Code.
 *
 * Usage:
 *   legacy-impact-audit install                  # user scope, auto-detect agent
 *   legacy-impact-audit install --agent opencode  # explicit agent
 *   legacy-impact-audit install --project ./repo  # project scope
 *   legacy-impact-audit update                    # re-install (same as install --force)
 *   legacy-impact-audit version
 */

const fs = require("node:fs");
const path = require("node:path");

const SKILL_NAME = "legacy-impact-audit";
const MARKER_START = "<!-- legacy-impact-audit:start -->";
const MARKER_END = "<!-- legacy-impact-audit:end -->";

// Where this npm package is installed (resolves to package root)
const PACKAGE_ROOT = path.resolve(__dirname, "..");
const SKILL_SOURCE = path.join(PACKAGE_ROOT, SKILL_NAME);

// Agent skill target directories (user scope)
const USER_SKILL_DIRS = {
  opencode: path.join(osHome(), ".config", "opencode", "skills"),
  codex: process.env.CODEX_HOME
    ? path.join(process.env.CODEX_HOME, "skills")
    : path.join(osHome(), ".codex", "skills"),
  claude: path.join(osHome(), ".claude", "skills"),
};

// Project scope directories
const PROJECT_SKILL_DIRS = {
  opencode: ".opencode/skills",
  claude: ".claude/skills",
};

const AGENTS_MD_TARGETS = {
  opencode: "AGENTS.md",
  codex: "AGENTS.md",
  claude: "CLAUDE.md",
};

function osHome() {
  return process.env.HOME || process.env.USERPROFILE || ".";
}

function detectAgent() {
  if (fs.existsSync(path.join(osHome(), ".config", "opencode"))) return "opencode";
  if (fs.existsSync(path.join(osHome(), ".codex"))) return "codex";
  if (fs.existsSync(path.join(osHome(), ".claude"))) return "claude";
  return "opencode"; // default
}

function copySkill(src, dest, force) {
  if (!fs.existsSync(src)) {
    console.error(`Skill source not found: ${src}`);
    process.exit(1);
  }
  if (fs.existsSync(dest)) {
    if (!force) {
      console.error(`Destination exists: ${dest}\nRe-run with --force to overwrite.`);
      process.exit(1);
    }
    fs.rmSync(dest, { recursive: true, force: true });
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  copyRecursive(src, dest);
  console.log(`Installed: ${dest}`);
}

function copyRecursive(src, dest) {
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
}

function instructionBlock(scriptPath) {
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
python3 "${scriptPath}/scripts/impact_audit.py" scan \\
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
  let content;
  const startIdx = existing.indexOf(MARKER_START);
  const endIdx = existing.indexOf(MARKER_END);
  if (startIdx !== -1 && endIdx !== -1) {
    const before = existing.substring(0, startIdx).trimEnd();
    const after = existing.substring(endIdx + MARKER_END.length).trimStart();
    content = `${before}\n\n${block.trim()}\n\n${after}\n`;
  } else {
    content = `${existing.trimEnd()}\n\n${block.trim()}\n`;
  }
  fs.writeFileSync(filePath, content, "utf-8");
  console.log(`Updated: ${filePath}`);
}

function resolveProjectRoot(rootArg) {
  if (rootArg) return path.resolve(rootArg);
  // walk up from cwd looking for AGENTS.md or .git
  let cwd = process.cwd();
  while (true) {
    if (fs.existsSync(path.join(cwd, ".git")) || fs.existsSync(path.join(cwd, "AGENTS.md")) || fs.existsSync(path.join(cwd, "CLAUDE.md"))) {
      return cwd;
    }
    const parent = path.dirname(cwd);
    if (parent === cwd) return process.cwd(); // hit filesystem root
    cwd = parent;
  }
}

function cmdInstall(args) {
  const agent = args.agent || detectAgent();
  const projectRoot = args.project ? resolveProjectRoot(args.project) : null;
  const scope = args.scope || (projectRoot ? "project" : "user");
  const force = args.force || false;

  if (!USER_SKILL_DIRS[agent]) {
    console.error(`Unknown agent: ${agent}. Supported: ${Object.keys(USER_SKILL_DIRS).join(", ")}`);
    process.exit(1);
  }

  if (scope === "user") {
    const targetDir = path.join(USER_SKILL_DIRS[agent], SKILL_NAME);
    copySkill(SKILL_SOURCE, targetDir, force);
  } else if (scope === "project") {
    if (!projectRoot) {
      console.error("Project scope requires a project root. Use --project <path> or run from within a git repo.");
      process.exit(1);
    }
    const skillDir = PROJECT_SKILL_DIRS[agent];
    if (!skillDir) {
      console.error(`Project scope not supported for agent: ${agent}`);
      process.exit(1);
    }
    const targetDir = path.join(projectRoot, skillDir, SKILL_NAME);
    copySkill(SKILL_SOURCE, targetDir, force);

    // Write AGENTS.md block for opencode/codex, or skip for claude (CLAUDE.md)
    if (AGENTS_MD_TARGETS[agent]) {
      const agentsMd = path.join(projectRoot, AGENTS_MD_TARGETS[agent]);
      const installedPath = targetDir.replace(/\\/g, "/");
      writeMarkedBlock(agentsMd, instructionBlock(installedPath));
    }
  }

  console.log(`\nlegacy-impact-audit v${require("../package.json").version} installed for ${agent} (${scope} scope).`);
  console.log("Prerequisites: python3 (or python) and ripgrep (rg) must be available in PATH.");
}

function cmdUpdate(args) {
  args.force = true;
  cmdInstall(args);
  console.log("Updated to latest version.");
}

function cmdVersion() {
  const pkg = require("../package.json");
  console.log(`legacy-impact-audit v${pkg.version}`);
}

function printHelp() {
  console.log(`\
legacy-impact-audit CLI — Install the skill for your coding agent.

Usage:
  legacy-impact-audit install [options]    Install the skill
  legacy-impact-audit update [options]     Re-install (force overwrite)
  legacy-impact-audit version              Show version
  legacy-impact-audit help                 Show this help

Options:
  --agent <agent>     Target agent: opencode, codex, claude (auto-detected)
  --project <path>    Install in project scope (works with --agent)
  --scope <scope>     user (default) or project
  --force             Overwrite existing installation
`);
}

function main() {
  const args = process.argv.slice(2);
  const cmd = args[0] || "help";

  const parsed = { agent: null, scope: null, project: null, force: false };
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--agent": parsed.agent = args[++i]; break;
      case "--scope": parsed.scope = args[++i]; break;
      case "--project": parsed.project = args[++i]; break;
      case "--force": parsed.force = true; break;
    }
  }

  switch (cmd) {
    case "install": cmdInstall(parsed); break;
    case "update": cmdUpdate(parsed); break;
    case "version": case "--version": case "-v": cmdVersion(); break;
    case "help": case "--help": case "-h": default: printHelp(); break;
  }
}

main();
