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

// Agent skill target directories (user scope), with a check path for detection
const USER_TARGETS = [
  { name: "opencode", checkDir: path.join(osHome(), ".config", "opencode"), skillDir: path.join(osHome(), ".config", "opencode", "skills", SKILL_NAME) },
  { name: "codex", checkDir: process.env.CODEX_HOME ? process.env.CODEX_HOME : path.join(osHome(), ".codex"), skillDir: path.join(
      process.env.CODEX_HOME ? process.env.CODEX_HOME : path.join(osHome(), ".codex"),
      "skills", SKILL_NAME
    ),
  },
  { name: "claude", checkDir: path.join(osHome(), ".claude"), skillDir: path.join(osHome(), ".claude", "skills", SKILL_NAME) },
  { name: "copilot", checkDir: path.join(osHome(), ".copilot"), skillDir: path.join(osHome(), ".copilot", "skills", SKILL_NAME) },
  { name: "deepcode", checkDir: path.join(osHome(), ".agents"), skillDir: path.join(osHome(), ".agents", "skills", SKILL_NAME) },
  { name: "gemini", checkDir: path.join(osHome(), ".gemini"), skillDir: path.join(osHome(), ".gemini", "skills", SKILL_NAME) },
];

// ── Agent capabilities matrix ──
// What each agent gets during install (user scope).
//   instruction: write a marked block to the agent's global config
//   skill:       copy skill files to the agent's skill directory
//   hook:        install a coding-agent hook (post-tool-edit audit reminder)
//
//   Hook types:
//     "opencode-plugin" �?copies audit-reminder.js to plugins/ directory
//     false             �?no hook available (relies on instruction block)
//
//   TODO: codex  �?"codex-hook" (format TBD)
//   TODO: copilot �?"copilot-hook" (format TBD)
const AGENT_CAPABILITIES = {
  opencode: { instruction: true, skill: true, hook: "opencode-plugin" },
  codex:    { instruction: true, skill: true, hook: "codex-session-hook" },
  claude:   { instruction: true, skill: true, hook: false },
  copilot:  { instruction: true, skill: true, hook: false },
  gemini:   { instruction: true, skill: true, hook: false },
  deepcode: { instruction: true, skill: true, hook: false },
};

// Instruction file targets per agent (for project scope installs)
const INSTRUCTION_TARGETS = {
  opencode: "AGENTS.md",
  codex: "AGENTS.md",
  claude: "CLAUDE.md",
  copilot: path.join(".github", "copilot-instructions.md"),
  gemini: "GEMINI.md",
  deepcode: path.join(".deepcode", "instructions.md"),
};

function osHome() {
  return process.env.HOME || process.env.USERPROFILE || ".";
}

// ── OS-aware command generation ──

function isWindows() {
  return process.platform === "win32";
}

function auditCommand(scriptPath) {
  const py = isWindows() ? "python" : "python3";
  const sep = isWindows() ? " \\\n  " : " \\\n  ";
  const pathSep = isWindows() ? "\\" : "/";
  const psPath = scriptPath.replace(/\//g, pathSep);
  return [
    `${py} "${psPath}/scripts/impact_audit.py" scan`,
    "--root . --symbol METHOD_NAME --owner-class OWNER_CLASS",
    "--owner-package OWNER_PACKAGE --definition-file path/to/OwnerClass.java",
  ].join(sep);
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
python3 "${scriptPath}/scripts/impact_audit.py" scan \\
  --root . --symbol METHOD_NAME --owner-class OWNER_CLASS \\
  --owner-package OWNER_PACKAGE --definition-file path/to/OwnerClass.java
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
    // Check if the agent's root config directory exists on this machine
    return fs.existsSync(t.checkDir);
  });

  if (found.length === 0) {
    // No known agent found �?try default (opencode)
    const target = USER_TARGETS.find(t => t.name === "opencode");
    if (target) {
      fs.mkdirSync(path.dirname(target.skillDir), { recursive: true });
      copyRecursive(SKILL_SOURCE, target.skillDir);
      console.log(`[legacy-impact-audit] Installed to ${target.skillDir}`);
    }
    return;
  }

  for (const target of found) {
    const caps = AGENT_CAPABILITIES[target.name] || { instruction: true, skill: true, hook: false };

    // 1. Copy skill files
    if (caps.skill) {
      const parent = path.dirname(target.skillDir);
      fs.mkdirSync(parent, { recursive: true });
      copyRecursive(SKILL_SOURCE, target.skillDir);
      console.log(`[legacy-impact-audit] Installed for ${target.name}: ${target.skillDir}`);
    }

    // 2. Write agent instruction block (AGENTS.md / CLAUDE.md / etc.)
    if (caps.instruction) {
      writeAgentHook(target);
    }

    // 3. Install coding-agent hook (post-tool-edit audit reminder)
    if (caps.hook) {
      installAgentHook(target, caps.hook);
    }
  }

  console.log("[legacy-impact-audit] Prerequisites: python (or python3) and ripgrep (rg) must be in PATH.");
  console.log("[legacy-impact-audit] For project scope: `legacy-impact-audit install --project ./repo`.");
}

// ── Agent instruction hooks ──
// Writes a block to each agent's global config telling the agent to run the
// impact audit before touching legacy Java code. Idempotent (marked block).

function writeAgentHook(target) {
  // Map agent to its global instruction file
  const INSTRUCTION_FILES = {
    opencode: path.join(target.checkDir, "AGENTS.md"),
    codex: path.join(target.checkDir, "AGENTS.md"),
    claude: path.join(target.checkDir, "CLAUDE.md"),
    copilot: path.join(target.checkDir, "copilot-instructions.md"),
    gemini: path.join(target.checkDir, "GEMINI.md"),
    deepcode: path.join(target.checkDir, "AGENTS.md"),
  };

  const instructionFile = INSTRUCTION_FILES[target.name];
  if (!instructionFile) return;

  // Skill path relative to the installed location
  const scriptPath = target.skillDir.replace(/\\/g, "/");
const cmd = auditCommand(scriptPath);
const fence = isWindows() ? "powershell" : "bash";
  const block = `\
<!-- legacy-impact-audit:start -->
## Legacy Impact Audit

### When to Run (MANDATORY — DO NOT BYPASS)
Run for ANY code change. No exceptions. Adding/modifying methods, classes,
fields, constructors, signatures, DTOs, entities, DAOs, queries, schemas,
any file write/edit/create = MUST RUN.The ONLY skip: pure read (query, search, read, explain), debug without changes.
If you think "this doesn't need an audit" — STOP. Run it anyway.

### Plan-First Gate
Before ANY code change: plan → audit → review → confirm → implement.
Use plan/brainstorm/ask-me/grill to validate first. MANDATORY.
Run audit BEFORE review — findings may change the plan.

### Mandatory Triggers
service methods, public APIs, shared utilities, job entry points, workflow
logic, DAO/query/persistence, DTO/table/JSON, financial calculation, scoring,
approval, reconciliation, core business logic.

### Gate Rules
- Do not proceed if audit returns \`REFINE_REQUIRED\`.
- Do not feed raw search results to LLM; use the generated report.
- Test/regression scope from \`real_dependency\` and \`possible_dependency\`.

\`\`\`${fence}
${cmd}
\`\`\`
<!-- legacy-impact-audit:end -->`;

  const dir = path.dirname(instructionFile);
  fs.mkdirSync(dir, { recursive: true });
  let existing = "";
  if (fs.existsSync(instructionFile)) {
    existing = fs.readFileSync(instructionFile, "utf-8");
  }
  // Idempotent: replace or append the marked block
  const startIdx = existing.indexOf("<!-- legacy-impact-audit:start -->");
  const endIdx = existing.indexOf("<!-- legacy-impact-audit:end -->");
  let content;
  if (startIdx !== -1 && endIdx !== -1) {
    const before = existing.substring(0, startIdx).trimEnd();
    const after = existing.substring(endIdx + "<!-- legacy-impact-audit:end -->".length).trimStart();
    content = `${before}\n\n${block.trim()}\n\n${after}\n`;
  } else {
    content = `${existing.trimEnd()}\n\n${block.trim()}\n`;
  }
  fs.writeFileSync(instructionFile, content, "utf-8");
  console.log(`[legacy-impact-audit]   Agent hook: ${instructionFile}`);
}

// ── Coding-agent hooks (per agent type) ──

function installAgentHook(target, hookType) {
  switch (hookType) {
    case "opencode-plugin":
      installOpenCodePlugin(target);
      break;
    case "codex-session-hook":
      installCodexSessionHook(target);
      break;
    // TODO: case "copilot-hook": installCopilotHook(target); break;
  }
}

function installCodexSessionHook(target) {
  const hookScript = path.join(target.skillDir, "scripts", "codex-session-start-hook.py");
  const hookConfig = path.join(target.checkDir, "hooks.json");
  const configToml = path.join(target.checkDir, "config.toml");

  // 1. Register the SessionStart hook in hooks.json
  let hooksConfig = {};
  if (fs.existsSync(hookConfig)) {
    try { hooksConfig = JSON.parse(fs.readFileSync(hookConfig, "utf-8")); } catch (_) {}
  }
  const hooks = hooksConfig.hooks || {};
  hooks.SessionStart = [
    {
      matcher: "startup",
      hooks: [
        {
          type: "command",
          command: `python3 "${hookScript.replace(/\\/g, '/')}"`,
          timeout: 10,
          statusMessage: "Running impact audit reminder...",
        },
      ],
    },
  ];
  // Merge with existing config (preserve other events)
  hooksConfig.hooks = { ...hooksConfig.hooks, ...hooks };
  fs.writeFileSync(hookConfig, JSON.stringify(hooksConfig, null, 2), "utf-8");
  console.log(`[legacy-impact-audit]   Hook (codex-session): ${hookConfig}`);

  // 2. Enable hooks feature in config.toml
  let toml = "";
  if (fs.existsSync(configToml)) {
    toml = fs.readFileSync(configToml, "utf-8");
  }
  if (!toml.includes("hooks = true")) {
    if (toml.includes("[features]")) {
      toml = toml.replace("[features]", "[features]\nhooks = true");
    } else {
      toml = toml.trimEnd() + "\n\n[features]\nhooks = true\n";
    }
    fs.writeFileSync(configToml, toml, "utf-8");
    console.log(`[legacy-impact-audit]   Enabled hooks in ${configToml}`);
  }
}

function installOpenCodePlugin(target) {
  const pluginSrc = path.join(SKILL_SOURCE, "opencode-hooks", "audit-reminder.js");
  const pluginDir = path.join(target.checkDir, "plugins");
  const pluginDest = path.join(pluginDir, "legacy-impact-audit.js");

  if (!fs.existsSync(pluginSrc)) return;
  fs.mkdirSync(pluginDir, { recursive: true });
  fs.copyFileSync(pluginSrc, pluginDest);
  console.log(`[legacy-impact-audit]   Hook (opencode-plugin): ${pluginDest}`);
}

function installCodexSessionHook(target) {
  // Write ~/.codex/hooks.json with SessionStart hook that injects audit context
  const hooksJsonPath = path.join(target.checkDir, "hooks.json");
  const hookScriptPath = path.join(target.skillDir, "scripts", "codex-session-start-hook.py")
    .replace(/\\/g, "/");

  const hooksConfig = {
    hooks: {
      SessionStart: [
        {
          matcher: "startup|resume",
          hooks: [
            {
              type: "command",
              command: `python3 "${hookScriptPath}"`,
              timeout: 5,
            },
          ],
        },
      ],
    },
  };

  // Merge with existing hooks.json if present
  let existing = {};
  if (fs.existsSync(hooksJsonPath)) {
    try { existing = JSON.parse(fs.readFileSync(hooksJsonPath, "utf-8")); } catch (_) {}
  }

  // Deep merge: add our SessionStart without overwriting other events
  if (!existing.hooks) existing.hooks = {};
  existing.hooks.SessionStart = [
    ...(existing.hooks.SessionStart || []),
    ...hooksConfig.hooks.SessionStart,
  ];

  fs.mkdirSync(path.dirname(hooksJsonPath), { recursive: true });
  fs.writeFileSync(hooksJsonPath, JSON.stringify(existing, null, 2), "utf-8");
  console.log(`[legacy-impact-audit]   Hook (codex-session-hook): ${hooksJsonPath}`);

  // Ensure hooks is enabled in config.toml (idempotent)
  ensureCodexHooksEnabled(target.checkDir);
}

function ensureCodexHooksEnabled(codexDir) {
  const configPath = path.join(codexDir, "config.toml");
  let config = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf-8") : "";

  // Check if hooks feature is already enabled
  if (/hooks\s*=\s*true/.test(config)) return;

  // Add [features] section with hooks = true
  if (config.includes("[features]")) {
    config = config.replace(/\[features\]/, "[features]\nhooks = true");
  } else {
    config += "\n[features]\nhooks = true\n";
  }
  fs.writeFileSync(configPath, config, "utf-8");
}

main();
