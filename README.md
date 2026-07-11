# Codex Personal Skills

This repository stores personal Codex skills for syncing across machines.

## Use on a new computer

1. Clone this private repository.
2. Run `setup-on-this-pc.ps1` from PowerShell.
3. Restart Codex or start a new task so the skills list is refreshed.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-on-this-pc.ps1
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
