# Git Backup Automation

## Run Backup

From the project root:

```bat
backup_git.bat
```

The batch file runs:

```bat
python scripts/git_backup.py --message "Auto backup CRM progress" --force-unlock
```

You can also run a custom message:

```bat
python scripts/git_backup.py --message "Your commit message" --force-unlock
```

## What The Script Does

1. Detects the current repository path.
2. Detects the current branch.
3. Detects `origin` remote.
4. Checks `.git/index.lock`.
5. Removes `.git/index.lock` when `--force-unlock` is used.
6. Runs `git status --short`.
7. Runs `git add .`.
8. Runs `git commit -m "<message>"`.
9. Runs `git push origin <current_branch>`.
10. Prints branch, commit hash, push status, and any error.

The script only reports success when the commit step succeeds or there is nothing to commit, and the push succeeds.

## If There Is Nothing To Commit

The script prints:

```text
No changes to commit
```

It still tries to push the current branch so remote status is verified where possible.

## Common Permission Denied Causes

On Windows, Git can fail with:

```text
Unable to create .git/index.lock: Permission denied
```

Common causes:

- Another Git process is still running.
- Another Python or Streamlit process is holding a file handle.
- `.git` became read-only.
- Windows permissions do not allow the current user to write `.git`.
- Antivirus or sync software temporarily locked repository files.

## Manual Fix Commands

Run these from the project root in Command Prompt:

```bat
taskkill /F /IM git.exe
taskkill /F /IM python.exe
attrib -R .git /S /D
icacls .git /grant %USERNAME%:F /T
```

Then retry:

```bat
backup_git.bat
```

## Notes

- The script pushes to the current branch, not a hardcoded branch.
- If the current branch is `master`, it pushes `origin master`.
- If the current branch is `main`, it pushes `origin main`.
- It never claims Git updated unless push succeeded.
