import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_MESSAGE = "Auto backup CRM progress"
PERMISSION_HINTS = [
    "taskkill /F /IM git.exe",
    "taskkill /F /IM python.exe",
    "attrib -R .git /S /D",
    "icacls .git /grant %USERNAME%:F /T",
]


def run_command(args, cwd, check=False):
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def print_command_result(result):
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip())


def find_repo_root(start_path):
    result = run_command(["git", "rev-parse", "--show-toplevel"], start_path)
    if result.returncode != 0:
        return None, result.stderr.strip() or result.stdout.strip()
    return Path(result.stdout.strip()).resolve(), ""


def get_current_branch(repo_path):
    result = run_command(["git", "branch", "--show-current"], repo_path)
    if result.returncode != 0:
        return "", result.stderr.strip() or result.stdout.strip()
    return result.stdout.strip(), ""


def get_remote(repo_path):
    result = run_command(["git", "remote", "get-url", "origin"], repo_path)
    if result.returncode != 0:
        return "", result.stderr.strip() or result.stdout.strip()
    return result.stdout.strip(), ""


def has_permission_denied(text):
    return "permission denied" in (text or "").lower() or "access is denied" in (text or "").lower()


def print_permission_help():
    print("Suggested Windows fix commands:")
    for command in PERMISSION_HINTS:
        print(f"  {command}")


def remove_index_lock(repo_path, force_unlock):
    lock_path = repo_path / ".git" / "index.lock"
    if not lock_path.exists():
        return True, ""

    print(f"Found Git lock file: {lock_path}")
    if not force_unlock:
        print("Run again with --force-unlock to remove .git/index.lock before backup.")
        return False, "index.lock exists"

    try:
        lock_path.unlink()
        print("Removed .git/index.lock")
        return True, ""
    except OSError:
        message = "index.lock is locked by another process or permission issue"
        print(message)
        print_permission_help()
        return False, message


def get_commit_hash(repo_path):
    result = run_command(["git", "rev-parse", "HEAD"], repo_path)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Create a safe Git backup commit and push.")
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="Commit message.")
    parser.add_argument("--force-unlock", action="store_true", help="Try to remove .git/index.lock before backup.")
    args = parser.parse_args()

    error = ""
    push_status = "not attempted"
    commit_hash = ""

    repo_path, repo_error = find_repo_root(Path.cwd())
    if not repo_path:
        print(f"Error: Could not detect Git repo. {repo_error}")
        return 1

    branch, branch_error = get_current_branch(repo_path)
    remote, remote_error = get_remote(repo_path)

    print(f"Repo: {repo_path}")
    print(f"Branch: {branch or '(detached or unknown)'}")
    print(f"Remote origin: {remote or '(missing)'}")

    if not branch:
        error = branch_error or "Current branch could not be detected."
        print(f"Error: {error}")
        return 1

    lock_ok, lock_error = remove_index_lock(repo_path, args.force_unlock)
    if not lock_ok:
        print(f"Branch: {branch}")
        print(f"Commit hash: {commit_hash or 'none'}")
        print(f"Push status: failed")
        print(f"Error: {lock_error}")
        return 1

    print("\nGit status:")
    status = run_command(["git", "status", "--short"], repo_path)
    print_command_result(status)
    if status.returncode != 0:
        error = status.stderr.strip() or status.stdout.strip()
        print(f"Error: {error}")
        return 1

    add_result = run_command(["git", "add", "."], repo_path)
    if add_result.returncode != 0:
        error = add_result.stderr.strip() or add_result.stdout.strip()
        print_command_result(add_result)
        if has_permission_denied(error):
            print_permission_help()
        print(f"Branch: {branch}")
        print(f"Commit hash: {commit_hash or 'none'}")
        print("Push status: failed")
        print(f"Error: {error}")
        return 1

    post_add_status = run_command(["git", "status", "--short"], repo_path)
    changes_to_commit = bool(post_add_status.stdout.strip())

    if changes_to_commit:
        commit_result = run_command(["git", "commit", "-m", args.message], repo_path)
        print_command_result(commit_result)
        if commit_result.returncode != 0:
            error = commit_result.stderr.strip() or commit_result.stdout.strip()
            if "nothing to commit" in error.lower():
                print("No changes to commit")
            else:
                if has_permission_denied(error):
                    print_permission_help()
                print(f"Branch: {branch}")
                print(f"Commit hash: {commit_hash or 'none'}")
                print("Push status: failed")
                print(f"Error: {error}")
                return 1
    else:
        print("No changes to commit")

    commit_hash = get_commit_hash(repo_path)

    push_result = run_command(["git", "push", "origin", branch], repo_path)
    print_command_result(push_result)
    if push_result.returncode != 0:
        error = push_result.stderr.strip() or push_result.stdout.strip()
        push_status = "failed"
        if has_permission_denied(error):
            print_permission_help()
        print(f"Branch: {branch}")
        print(f"Commit hash: {commit_hash or 'none'}")
        print(f"Push status: {push_status}")
        print(f"Error: {error}")
        return 1

    push_status = "succeeded"
    print(f"Branch: {branch}")
    print(f"Commit hash: {commit_hash or 'none'}")
    print(f"Push status: {push_status}")
    if error:
        print(f"Error: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
