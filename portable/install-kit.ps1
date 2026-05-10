param(
    [string]$Agent = "codex",
    [ValidateSet("user", "project")]
    [string]$Scope = "user",
    [string]$ProjectRoot = ".",
    [string]$SkillsDir = "",
    [string]$Source = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$SkillName = "legacy-impact-audit"
$MarkerStart = "<!-- legacy-impact-audit:start -->"
$MarkerEnd = "<!-- legacy-impact-audit:end -->"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KitRoot = Resolve-Path (Join-Path $ScriptDir "..")

if ([string]::IsNullOrWhiteSpace($Source)) {
    $Source = Join-Path $KitRoot $SkillName
}
$Source = (Resolve-Path $Source).Path
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

if (-not (Test-Path (Join-Path $Source "SKILL.md"))) {
    throw "Source skill not found: $Source"
}

function Copy-Skill {
    param(
        [string]$SourcePath,
        [string]$DestinationParent
    )

    $destination = Join-Path $DestinationParent $SkillName
    if (Test-Path $destination) {
        if (-not $Force) {
            throw "Destination exists: $destination. Re-run with -Force to overwrite."
        }
        Remove-Item $destination -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
    New-Item -ItemType Directory -Force -Path $destination | Out-Null

    Get-ChildItem -Path $SourcePath -Force -Recurse | ForEach-Object {
        $normalized = $_.FullName.Replace("\", "/")
        if (
            $normalized -match "/__pycache__(/|$)" -or
            $normalized -match "/\.git(/|$)" -or
            $_.Name -like "*.pyc" -or
            $_.Name -eq ".DS_Store"
        ) {
            return
        }

        $relative = $_.FullName.Substring($SourcePath.Length).TrimStart(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
        $target = Join-Path $destination $relative

        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Force -Path $target | Out-Null
        } else {
            $targetParent = Split-Path -Parent $target
            if ($targetParent) {
                New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
            }
            Copy-Item -Path $_.FullName -Destination $target -Force
        }
    }
    return $destination
}

function New-InstructionBlock {
    param([string]$ScriptPath)

    $Fence = '```'
    return @"
$MarkerStart
## Legacy Impact Audit

Before planning or implementing risky legacy Java changes, run a legacy impact audit.

Mandatory triggers:
- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, workflow, or other core business logic

Gate rules:
- Run impact audit before finalizing the implementation plan.
- Run it again after code changes and before functional test case design or code review.
- Do not proceed if the audit returns ``REFINE_REQUIRED``; narrow by owner class, package, module, or definition file first.
- Do not ask an LLM to analyze broad raw search results; use the generated audit report and packet.
- Test scope and regression scope must be derived from confirmed ``real_dependency`` and ``possible_dependency`` candidates.

Command pattern:

${Fence}bash
python3 "$ScriptPath" scan \
  --root . \
  --symbol METHOD_NAME \
  --owner-class OWNER_CLASS \
  --owner-package OWNER_PACKAGE \
  --definition-file path/to/OwnerClass.java
${Fence}
$MarkerEnd
"@
}

function Add-MarkedBlock {
    param(
        [string]$Path,
        [string]$ScriptPath
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    $block = New-InstructionBlock -ScriptPath $ScriptPath
    $existing = ""
    if (Test-Path $Path) {
        $existing = Get-Content -Raw -Encoding UTF8 -Path $Path
    }

    $pattern = [regex]::Escape($MarkerStart) + "(?s).*?" + [regex]::Escape($MarkerEnd)
    if ($existing -match [regex]::Escape($MarkerStart) -and $existing -match [regex]::Escape($MarkerEnd)) {
        $content = [regex]::Replace($existing, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block }, 1)
    } elseif ([string]::IsNullOrWhiteSpace($existing)) {
        $content = $block + [Environment]::NewLine
    } else {
        $content = $existing.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + $block + [Environment]::NewLine
    }

    Set-Content -Encoding UTF8 -Path $Path -Value $content
}

function Get-UserParent {
    param([string]$Name)

    switch ($Name) {
        "codex" {
            if ($env:CODEX_HOME) {
                return (Join-Path $env:CODEX_HOME "skills")
            }
            return (Join-Path $HOME ".codex/skills")
        }
        "claude" { return (Join-Path $HOME ".claude/skills") }
        "opencode" { return (Join-Path $HOME ".config/opencode/skills") }
        "copilot" { return (Join-Path $HOME ".copilot/skills") }
        "deepcode" { return (Join-Path $HOME ".agents/skills") }
        default { throw "User-scope install is not defined for $Name" }
    }
}

function Get-ProjectParent {
    param([string]$Name)

    switch ($Name) {
        "claude" { return (Join-Path $ProjectRoot ".claude/skills") }
        "opencode" { return (Join-Path $ProjectRoot ".opencode/skills") }
        "copilot" { return (Join-Path $ProjectRoot ".github/skills") }
        "deepcode" { return (Join-Path $ProjectRoot ".deepcode/skills") }
        default { throw "Project-scope install is not defined for $Name" }
    }
}

function Install-Agent {
    param([string]$Name)

    if ($Name -eq "codex" -and -not [string]::IsNullOrWhiteSpace($SkillsDir)) {
        $installed = Copy-Skill -SourcePath $Source -DestinationParent $SkillsDir
        Write-Output "Installed/updated: $installed"
        return
    }

    if ($Name -eq "gemini") {
        if ($Scope -eq "user") {
            $installed = Copy-Skill -SourcePath $Source -DestinationParent (Join-Path $HOME ".agents/skills")
            $geminiFile = Join-Path $HOME ".gemini/GEMINI.md"
            Add-MarkedBlock -Path $geminiFile -ScriptPath (Join-Path $installed "scripts/impact_audit.py")
            Write-Output "Installed/updated: $installed"
            Write-Output "Installed/updated: $geminiFile"
        } else {
            $installed = Copy-Skill -SourcePath $Source -DestinationParent (Join-Path $ProjectRoot ".ai/legacy-impact-audit/skills")
            $geminiFile = Join-Path $ProjectRoot "GEMINI.md"
            Add-MarkedBlock -Path $geminiFile -ScriptPath (Join-Path $installed "scripts/impact_audit.py")
            Write-Output "Installed/updated: $installed"
            Write-Output "Installed/updated: $geminiFile"
        }
        return
    }

    if ($Scope -eq "user") {
        $installed = Copy-Skill -SourcePath $Source -DestinationParent (Get-UserParent -Name $Name)
        Write-Output "Installed/updated: $installed"
        return
    }

    $installed = Copy-Skill -SourcePath $Source -DestinationParent (Get-ProjectParent -Name $Name)
    Write-Output "Installed/updated: $installed"

    if ($Name -eq "opencode") {
        $agentsFile = Join-Path $ProjectRoot "AGENTS.md"
        Add-MarkedBlock -Path $agentsFile -ScriptPath (Join-Path $installed "scripts/impact_audit.py")
        Write-Output "Installed/updated: $agentsFile"
    } elseif ($Name -eq "copilot") {
        $copilotFile = Join-Path $ProjectRoot ".github/copilot-instructions.md"
        Add-MarkedBlock -Path $copilotFile -ScriptPath (Join-Path $installed "scripts/impact_audit.py")
        Write-Output "Installed/updated: $copilotFile"
    }
}

if ($Agent -eq "all") {
    $agents = @("codex", "claude", "opencode", "gemini", "copilot", "deepcode")
} else {
    $agents = $Agent -split "[,\s]+" | ForEach-Object { $_.Trim().ToLowerInvariant() } | Where-Object { $_ }
}

foreach ($name in $agents) {
    if ($name -notin @("codex", "claude", "opencode", "gemini", "copilot", "deepcode")) {
        throw "Unknown agent: $name"
    }
    Install-Agent -Name $name
}
