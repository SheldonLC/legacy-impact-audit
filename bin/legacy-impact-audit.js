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
  copilot: path.join(osHome(), ".copilot", "skills"),
  deepcode: path.join(osHome(), ".agents", "skills"),
  gemini: path.join(osHome(), ".agents", "skills"),
};

// Project scope directories
const PROJECT_SKILL_DIRS = {
  opencode: ".opencode/skills",
  claude: ".claude/skills",
  copilot: path.join(".github", "skills"),
  deepcode: path.join(".deepcode", "skills"),
  gemini: path.join(".ai", "legacy-impact-audit", "skills"),
};

const AGENTS_MD_TARGETS = {
  opencode: "AGENTS.md",
  codex: "AGENTS.md",
  claude: "CLAUDE.md",
  gemini: "GEMINI.md",
  copilot: path.join(".github", "copilot-instructions.md"),
  deepcode: path.join(".deepcode", "instructions.md"),
};

// ── Agent capabilities: what each agent gets during install ──
//   hook types: "opencode-plugin" = copies audit-reminder.js to plugins/ dir
//               false = no hook available (relies on instruction block)
const AGENT_CAPABILITIES = {
  opencode: { instruction: true, skill: true, hook: "opencode-plugin" },
  codex:    { instruction: true, skill: true, hook: "codex-session-hook" },
  claude:   { instruction: true, skill: true, hook: false },
  copilot:  { instruction: true, skill: true, hook: false },
  gemini:   { instruction: true, skill: true, hook: false },
  deepcode: { instruction: true, skill: true, hook: false },
};

function osHome() {
  return process.env.HOME || process.env.USERPROFILE || ".";
}

function detectAgent() {
  if (fs.existsSync(path.join(osHome(), ".config", "opencode"))) return "opencode";
  if (fs.existsSync(path.join(osHome(), ".codex"))) return "codex";
  if (fs.existsSync(path.join(osHome(), ".claude"))) return "claude";
  if (fs.existsSync(path.join(osHome(), ".copilot"))) return "copilot";
  if (fs.existsSync(path.join(osHome(), ".gemini"))) return "gemini";
  if (fs.existsSync(path.join(osHome(), ".agents"))) return "deepcode";
  return "opencode"; // default
}

function preferredPythonCommand() {
  return process.platform === "win32" ? "python" : "python3";
}

function sessionHookCommand(scriptPath) {
  return `${preferredPythonCommand()} "${scriptPath.replace(/\\/g, "/")}"`;
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

function installHook(projectRoot, installedSkillDir) {
  const hooksDir = path.join(projectRoot, ".git", "hooks");
  if (!fs.existsSync(hooksDir)) {
    console.log("[legacy-impact-audit] No .git/hooks directory found — skipping hook install.");
    return;
  }
  const validatorPath = path.join(installedSkillDir, "scripts", "validate_impact_audit.py")
    .replace(/\\/g, "/");
  const reportPath = ".ai/legacy-impact-audit/impact-report.md";
  const maxAge = 240;

  // Generate hook with the correct installed path baked in
  const hookScript = `\
#!/usr/bin/env bash
set -euo pipefail
# Installed by legacy-impact-audit — validates impact audit artifacts exist before commit.
VALIDATOR="${validatorPath}"
PYTHON="$(command -v python3 || command -v python || echo '')"
if [ -f "$VALIDATOR" ]; then
  if [ -n "$PYTHON" ]; then
    "$PYTHON" "$VALIDATOR" --root . --mode staged --max-age-minutes ${maxAge}
    exit $?
  fi
fi
# Shell fallback — check report freshness
CHANGED="$(git diff --cached --name-only -- '*.java' '*.xml' '*.properties' '*.sql' | head -n 1 || true)"
if [ -z "$CHANGED" ]; then exit 0; fi
REPORT="${reportPath}"
if [ ! -f "$REPORT" ]; then
  echo "Impact report missing. Run legacy-impact-audit before committing risky Java changes." >&2
  exit 1
fi
NOW="$(date +%s)"
MTIME="$([ -n "$PYTHON" ] && "$PYTHON" -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$REPORT" 2>/dev/null ||
  stat -c %Y "$REPORT" 2>/dev/null || stat -f %m "$REPORT" 2>/dev/null || echo 0)"
if [ "$MTIME" -eq 0 ]; then
  echo "Could not determine impact report age. Re-run legacy-impact-audit." >&2
  exit 1
fi
AGE="$(( (NOW - MTIME) / 60 ))"
if [ "$AGE" -gt "${maxAge}" ]; then
  echo "Impact report is older than ${maxAge} minutes. Re-run legacy-impact-audit." >&2
  exit 1
fi
`;

  const hookDest = path.join(hooksDir, "pre-commit");
  fs.writeFileSync(hookDest, hookScript, { mode: 0o755 });
  console.log(`[legacy-impact-audit] Pre-commit hook installed: ${hookDest}`);
}

// ── Agent config hooks ──
// Writes a marked block to the agent's global config file so the coding agent
// always knows to run the audit before touching legacy Java code.

const AGENT_CONFIG_HOOKS = {
  opencode: { dir: path.join(osHome(), ".config", "opencode"), file: "AGENTS.md" },
  codex: { dir: process.env.CODEX_HOME || path.join(osHome(), ".codex"), file: "AGENTS.md" },
  claude: { dir: path.join(osHome(), ".claude"), file: "CLAUDE.md" },
  copilot: { dir: path.join(osHome(), ".copilot"), file: "copilot-instructions.md" },
  gemini: { dir: path.join(osHome(), ".gemini"), file: "GEMINI.md" },
  deepcode: { dir: path.join(osHome(), ".agents"), file: "AGENTS.md" },
};

function writeAgentConfigHook(agent, installedSkillDir) {
  const cfg = AGENT_CONFIG_HOOKS[agent];
  if (!cfg) return;
  const targetFile = path.join(cfg.dir, cfg.file);
  const scriptPath = installedSkillDir.replace(/\\/g, "/");
  const py = preferredPythonCommand();
  const fence = process.platform === "win32" ? "powershell" : "bash";
  const cmd = `${py} "${scriptPath}/scripts/impact_audit.py" scan --root . --symbol METHOD_NAME --owner-class OWNER_CLASS --owner-package OWNER_PACKAGE --definition-file path/to/OwnerClass.java`;
  const block = `\
<!-- legacy-impact-audit:start -->
## Legacy Impact Audit

### When to Run

Run the impact audit ONLY when you are about to make code changes:
- Implementing, fixing, refactoring, or modifying behavior
- Changing method signatures, DTO/table/query shapes, or public APIs

Do NOT trigger on: querying, debugging (without code changes), investigating, explaining, or case checking.

### Plan-First Gate

Before ANY code change: plan → audit → review → confirm → implement.
Use plan/brainstorm/ask-me/grill to validate the approach first.
Run the impact audit BEFORE review — audit findings may change the plan.
This gate is MANDATORY. You cannot skip it. You cannot rationalize a bypass.
Adding a method, changing a signature, modifying any file = MUST RUN.
Do not touch code until the plan is confirmed.

### Mandatory Triggers
- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, or core business logic

Gate rules:
- Do not proceed if the audit returns \`REFINE_REQUIRED\`.
- Do not ask an LLM to analyze raw search results; use the generated report.
- Test/regression scope from \`real_dependency\` and \`possible_dependency\`.

\`\`\`${fence}
${cmd}
\`\`\`
<!-- legacy-impact-audit:end -->`;

  writeMarkedBlock(targetFile, block);
  console.log(`[legacy-impact-audit] Agent hook: ${targetFile}`);
}

// ── Coding-agent hooks (per agent type) ──

function installAgentHook(agent, hookType) {
  switch (hookType) {
    case "opencode-plugin":
      installOpenCodePlugin();
      break;
    case "codex-session-hook":
      installCodexSessionHook();
      break;
    case "copilot-repo-hook":
      // Copilot hooks are per-repo only — handled in project scope install
      break;
  }
}

function installOpenCodePlugin() {
  const pluginSrc = path.join(SKILL_SOURCE, "opencode-hooks", "audit-reminder.js");
  if (!fs.existsSync(pluginSrc)) return;
  const pluginDir = path.join(osHome(), ".config", "opencode", "plugins");
  const pluginDest = path.join(pluginDir, "legacy-impact-audit.js");
  fs.mkdirSync(pluginDir, { recursive: true });
  fs.copyFileSync(pluginSrc, pluginDest);
  console.log(`[legacy-impact-audit] Hook (opencode-plugin): ${pluginDest}`);
}

function installCodexSessionHook() {
  const codexDir = process.env.CODEX_HOME || path.join(osHome(), ".codex");
  const skillDir = path.join(codexDir, "skills", SKILL_NAME);
  const hookScript = path.join(skillDir, "scripts", "codex-session-start-hook.py");
  const hookConfig = path.join(codexDir, "hooks.json");
  const configToml = path.join(codexDir, "config.toml");

  // Register SessionStart hook
  let hooksConfig = {};
  if (fs.existsSync(hookConfig)) {
    try { hooksConfig = JSON.parse(fs.readFileSync(hookConfig, "utf-8")); } catch (_) {}
  }
  const hooks = hooksConfig.hooks || {};
  hooks.SessionStart = [
    {
      matcher: "startup",
      hooks: [{ type: "command", command: sessionHookCommand(hookScript), timeout: 10 }],
    },
  ];
  hooksConfig.hooks = { ...hooksConfig.hooks, ...hooks };
  fs.writeFileSync(hookConfig, JSON.stringify(hooksConfig, null, 2), "utf-8");
  console.log(`[legacy-impact-audit] Hook (codex-session): ${hookConfig}`);

  // Enable hooks feature
  let toml = fs.existsSync(configToml) ? fs.readFileSync(configToml, "utf-8") : "";
  if (!toml.includes("hooks = true")) {
    toml = toml.includes("[features]")
      ? toml.replace("[features]", "[features]\nhooks = true")
      : toml.trimEnd() + "\n\n[features]\nhooks = true\n";
    fs.writeFileSync(configToml, toml, "utf-8");
    console.log(`[legacy-impact-audit]   Enabled hooks in config.toml`);
  }
}

function instructionBlock(scriptPath) {
  const py = process.platform === "win32" ? "python" : "python3";
  const fence = process.platform === "win32" ? "powershell" : "bash";
  const lineCont = process.platform === "win32" ? " \\\n  " : " \\\n  ";
  const psPath = process.platform === "win32" ? scriptPath.replace(/\//g, "\\") : scriptPath;
  const cmd = [
    `${py} "${psPath}/scripts/impact_audit.py" scan`,
    "--root . --symbol METHOD_NAME --owner-class OWNER_CLASS",
    "--owner-package OWNER_PACKAGE --definition-file path/to/OwnerClass.java",
  ].join(lineCont);

  return `\
${MARKER_START}
## Legacy Impact Audit

### When to Run (MANDATORY — DO NOT BYPASS)

Run the impact audit for ANY code change. No exceptions:
- Adding/modifying methods, classes, fields, constructors
- Changing signatures, return types, parameters, visibility
- Modifying DTOs, entities, DAOs, queries, table schemas
- Any file write, edit, or creation in the codebase

The ONLY operations that skip the audit:
- Pure read: querying, searching, reading files, explaining
- Debugging without code changes, investigating, answering questions

IMPORTANT: If you find yourself thinking "this is just a small change" or
"this doesn't need an audit" — STOP. You are rationalizing a bypass.
Run the audit anyway. Adding an overloaded method IS a public API change.
Even adding a comment requires you to consider downstream impact.

### Plan-First Gate

Before ANY code change: plan → audit → review → confirm → implement.
Use plan / brainstorm / ask-me / grill skills to validate the approach.
Run the impact audit BEFORE review — audit findings may change the plan.
Do not touch code until the plan is confirmed.

### Mandatory Triggers

When changing: service methods, public APIs, shared utilities, job entry points,
workflow logic, DAO/query/persistence, DTO/table/JSON contracts, financial
calculation, scoring, approval, reconciliation, or core business logic.

### Gate Rules

- Run audit before finalizing the plan and again before code review.
- Do not proceed if audit returns \`REFINE_REQUIRED\`.
- Do not feed raw search results to an LLM; use the generated report.
- Test/regression scope from \`real_dependency\` and \`possible_dependency\`.

### Command

\`\`\`${fence}
${cmd}
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
  const installHooks = args.hooks || false;

  if (!USER_SKILL_DIRS[agent]) {
    console.error(`Unknown agent: ${agent}. Supported: ${Object.keys(USER_SKILL_DIRS).join(", ")}`);
    process.exit(1);
  }

  if (scope === "user") {
    const targetDir = path.join(USER_SKILL_DIRS[agent], SKILL_NAME);
    copySkill(SKILL_SOURCE, targetDir, force);

    const caps = AGENT_CAPABILITIES[agent] || { instruction: true, skill: false, hook: false };

    if (caps.instruction) {
      writeAgentConfigHook(agent, targetDir);
    }
    if (caps.hook) {
      installAgentHook(agent, caps.hook);
    }
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

    // Write instruction file for this agent (AGENTS.md, CLAUDE.md, etc.)
    if (AGENTS_MD_TARGETS[agent]) {
      const agentsMd = path.join(projectRoot, AGENTS_MD_TARGETS[agent]);
      const installedPath = targetDir.replace(/\\/g, "/");
      writeMarkedBlock(agentsMd, instructionBlock(installedPath));
    }

    if (installHooks) {
      installHook(projectRoot, targetDir);
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

// ── Global hooks (git core.hooksPath) ──
const GLOBAL_HOOKS_DIR = path.join(osHome(), ".config", "legacy-impact-audit", "hooks");

function cmdHooks(args) {
  const action = args._sub || "status";

  if (action === "install") {
    fs.mkdirSync(GLOBAL_HOOKS_DIR, { recursive: true });
    generateGlobalHook(GLOBAL_HOOKS_DIR);
    setGitConfig();
    console.log(`[legacy-impact-audit] Global hooks installed.`);
    console.log(`  Hook dir: ${GLOBAL_HOOKS_DIR}`);
    console.log(`  All repos with .ai/legacy-impact-audit/ artifacts will be validated on commit.`);
    console.log(`  Repos without audit artifacts pass through silently.`);
  } else if (action === "uninstall") {
    unsetGitConfig();
    console.log("[legacy-impact-audit] Global hooks uninstalled.");
  } else {
    checkHookStatus();
  }
}

function generateGlobalHook(hooksDir) {
  const hookPath = path.join(hooksDir, "pre-commit");
  // The hook only gates repos that already have audit artifacts.
  const hook = [
    "#!/usr/bin/env bash",
    "# legacy-impact-audit global pre-commit hook",
    "# Only validates repos that already have impact audit artifacts.",
    "set -euo pipefail",
    'AUDIT_FILE=".ai/legacy-impact-audit/impact-scan.json"',
    'if [ ! -f "$AUDIT_FILE" ]; then exit 0; fi',
    'PYTHON="$(command -v python3 || command -v python || echo \'\')"',
    'if [ -z "$PYTHON" ]; then',
    '  echo "[legacy-impact-audit] Python not found — skipping audit validation." >&2',
    "  exit 0",
    "fi",
    "# Find the validator in known skill locations",
    "VALIDATOR=\"\"",
    "for dir in \\",
    '  "${LEGACY_IMPACT_AUDIT_HOME:-}" \\',
    '  "${CODEX_HOME:-}/skills" \\',
    '  "$HOME/.config/opencode/skills" \\',
    '  "$HOME/.codex/skills" \\',
    '  "$HOME/.claude/skills" \\',
    '  "$HOME/.copilot/skills" \\',
    '  "$HOME/.agents/skills"; do',
    '  if [ -f "$dir/legacy-impact-audit/scripts/validate_impact_audit.py" ]; then',
    '    VALIDATOR="$dir/legacy-impact-audit/scripts/validate_impact_audit.py"',
    "    break",
    "  fi",
    "done",
    'if [ -z "$VALIDATOR" ]; then',
    '  echo "[legacy-impact-audit] Validator not found — skipping." >&2',
    "  exit 0",
    "fi",
    '"$PYTHON" "$VALIDATOR" --root . --mode staged --max-age-minutes 240',
    "exit $?",
    "",
  ].join("\n");
  fs.writeFileSync(hookPath, hook, { mode: 0o755 });
}

function setGitConfig() {
  const { execSync } = require("child_process");
  try {
    execSync(`git config --global core.hooksPath "${GLOBAL_HOOKS_DIR.replace(/\\/g, '/')}"`,
      { stdio: "pipe", timeout: 5000 });
    execSync("git config --global legacy-impact-audit.hooksPath-set true",
      { stdio: "pipe", timeout: 5000 });
  } catch (e) { /* git not installed */ }
}

function unsetGitConfig() {
  const { execSync } = require("child_process");
  try {
    execSync("git config --global --unset core.hooksPath", { stdio: "pipe", timeout: 5000 });
    execSync("git config --global --unset legacy-impact-audit.hooksPath-set", { stdio: "pipe", timeout: 5000 });
  } catch (e) { /* already unset */ }
}

function checkHookStatus() {
  const { execSync } = require("child_process");
  try {
    const hooksPath = execSync("git config --global core.hooksPath", { encoding: "utf-8", timeout: 5000 }).trim();
    const isSet = execSync("git config --global legacy-impact-audit.hooksPath-set", { encoding: "utf-8", timeout: 5000 }).trim();
    console.log(`Global hooks: ${isSet === "true" ? "INSTALLED" : "UNKNOWN"}`);
    console.log(`  core.hooksPath: ${hooksPath}`);
    if (fs.existsSync(path.join(GLOBAL_HOOKS_DIR, "pre-commit"))) {
      console.log(`  Hook file: ${path.join(GLOBAL_HOOKS_DIR, "pre-commit")} (exists)`);
    }
    console.log(`\nInstall:   legacy-impact-audit hooks install`);
    console.log(`Uninstall: legacy-impact-audit hooks uninstall`);
  } catch (e) {
    console.log("Global hooks: NOT INSTALLED");
    console.log(`\nInstall: legacy-impact-audit hooks install`);
  }
}

function printHelp() {
  console.log(`\
legacy-impact-audit CLI — Install the skill for your coding agent.

Usage:
  legacy-impact-audit install [options]    Install the skill
  legacy-impact-audit update [options]     Re-install (force overwrite)
  legacy-impact-audit hooks [install|uninstall|status]  Manage global git hooks
  legacy-impact-audit version              Show version
  legacy-impact-audit help                 Show this help

Options:
  --agent <agent>     Target agent: opencode, codex, claude, copilot, gemini, deepcode (auto-detected)
  --project <path>    Install in project scope (writes instruction file for agent)
  --scope <scope>     user (default) or project
  --hooks             Install pre-commit hook (project scope only, opt-in)
  --force             Overwrite existing installation
`);
}

function main() {
  const args = process.argv.slice(2);
  const cmd = args[0] || "help";

  const parsed = { agent: null, scope: null, project: null, force: false, hooks: false };
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--agent": parsed.agent = args[++i]; break;
      case "--scope": parsed.scope = args[++i]; break;
      case "--project": parsed.project = args[++i]; break;
      case "--hooks": parsed.hooks = true; break;
      case "--force": parsed.force = true; break;
    }
  }

  switch (cmd) {
    case "install": cmdInstall(parsed); break;
    case "update": cmdUpdate(parsed); break;
    case "hooks": parsed._sub = args[1]; cmdHooks(parsed); break;
    case "version": case "--version": case "-v": cmdVersion(); break;
    case "help": case "--help": case "-h": default: printHelp(); break;
  }
}

main();
