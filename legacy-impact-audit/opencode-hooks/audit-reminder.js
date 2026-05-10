/**
 * legacy-impact-audit — OpenCode Plugin Hook
 *
 * Fires after every file edit/write. Checks whether the changed file is a
 * Java source/config file and whether a fresh impact audit exists.
 *
 * Install: copy to ~/.config/opencode/plugins/ (auto-installed by postinstall)
 * Or add to opencode.json: "plugin": ["legacy-impact-audit"]
 *
 * This plugin does NOT call Python or LLMs. It only checks for the presence
 * and freshness of existing audit artifacts. It warns the agent via an
 * injected message when the audit is missing or stale.
 */

export const LegacyImpactAuditPlugin = async ({ project, directory, worktree, client }) => {
  const auditDir = ".ai/legacy-impact-audit";
  const scanJson = `${auditDir}/impact-scan.json`;
  const reportMd = `${auditDir}/impact-report.md`;

  // File types that trigger an audit check
  const watched = [".java", ".xml", ".properties", ".sql", ".jsp", ".jspx", ".groovy", ".kt", ".scala"];

  return {
    "tool.execute.after": async (input, output) => {
      // Only check after edit/write tools
      if (input.tool !== "edit" && input.tool !== "write") return;

      // Get the file path that was modified
      const filePath = output?.args?.filePath || input?.args?.filePath;
      if (!filePath) return;

      // Check if it's a watched file type
      const ext = "." + filePath.split(".").pop().toLowerCase();
      if (!watched.includes(ext)) return;

      // Resolve repo root
      const { execSync } = await import("child_process");
      let repoRoot = worktree || directory;
      try {
        repoRoot = execSync("git rev-parse --show-toplevel", {
          cwd: directory, encoding: "utf-8", timeout: 3000,
        }).trim();
      } catch (_) { /* not a git repo, use CWD */ }

      const fs = await import("fs");
      const path = await import("path");

      const auditFile = path.join(repoRoot, scanJson);
      const reportFile = path.join(repoRoot, reportMd);

      // Check if audit artifacts exist
      if (!fs.existsSync(auditFile)) {
        // Remind the agent to run an audit — inject a message
        return output?.message
          ? `${output.message}\n\n[legacy-impact-audit] No impact audit found for ${path.basename(filePath)}. Run: legacy-impact-audit or \`python3 <skill>/scripts/impact_audit.py scan ...\``
          : output;
      }

      // Check freshness: audit older than the changed file?
      try {
        const fileMtime = fs.statSync(filePath).mtimeMs;
        const auditMtime = fs.statSync(auditFile).mtimeMs;
        const ageMinutes = Math.round((Date.now() - auditMtime) / 60000);

        if (ageMinutes > 240) {
          const warn = `[legacy-impact-audit] Impact audit is ${ageMinutes}min old (> 240min limit). Re-run the audit before committing changes to ${path.basename(filePath)}.`;
          return output?.message
            ? `${output.message}\n\n${warn}`
            : output;
        }
      } catch (_) { /* stat failed — skip freshness check */ }
    },
  };
};
