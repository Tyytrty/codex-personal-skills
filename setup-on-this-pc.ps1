param(
  [string]$SkillRoot = "$env:USERPROFILE\.codex\skills"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ResolvedRepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

if (-not (Test-Path -LiteralPath $SkillRoot)) {
  New-Item -ItemType Directory -Path $SkillRoot -Force | Out-Null
}

$ResolvedSkillRoot = (Resolve-Path -LiteralPath $SkillRoot).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path (Split-Path -Parent $ResolvedSkillRoot) "skills-backup-before-github-sync-$timestamp"

$skills = Get-ChildItem -LiteralPath $ResolvedRepoRoot -Directory |
  Where-Object {
    $_.Name -notin @(".git", ".github") -and
    (Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md"))
  }

if ($skills.Count -eq 0) {
  throw "No skill directories with SKILL.md were found in $ResolvedRepoRoot"
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

foreach ($skill in $skills) {
  $dest = Join-Path $ResolvedSkillRoot $skill.Name

  if (Test-Path -LiteralPath $dest) {
    $existing = Get-Item -LiteralPath $dest -Force
    $isLink = ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0

    if ($isLink) {
      Remove-Item -LiteralPath $dest -Force
    } else {
      Move-Item -LiteralPath $dest -Destination (Join-Path $backupRoot $skill.Name)
    }
  }

  New-Item -ItemType Junction -Path $dest -Target $skill.FullName | Out-Null
  Write-Host "Linked $($skill.Name)"
}

Write-Host ""
Write-Host "Done. Existing non-linked skills were backed up to:"
Write-Host $backupRoot

