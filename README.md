# Codex Personal Skills

This repository stores personal Codex skills for syncing across machines.

## Use on a new computer

1. Clone this private repository.
2. Copy or junction each skill directory into `%USERPROFILE%\.codex\skills`.
3. Restart Codex or start a new task so the skills list is refreshed.

Example junction command in PowerShell:

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\Humanizer-zh" `
  -Target "D:\codex-personal-skills\Humanizer-zh"
```

## Daily workflow

After editing skills on one computer:

```powershell
git add .
git commit -m "Update skills"
git push
```

On another computer:

```powershell
git pull --rebase
```

