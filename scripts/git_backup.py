import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_MESSAGE = "Auto backup CRM progress"
APP_LOCK_STALE_SECONDS = 30 * 60
GIT_LOCK_STALE_SECONDS = 5 * 60
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


def lock_age_seconds(lock_path):
    return time.time() - lock_path.stat().st_mtime


def acquire_app_lock(repo_path):
    lock_path = repo_path / "data" / "git_backup_running.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        age = lock_age_seconds(lock_path)
        if age > APP_LOCK_STALE_SECONDS:
            try:
                lock_path.unlink()
                print("Removed stale application backup lock.")
            except OSError:
                return None, "Another backup appears to be running and the lock cannot be removed."
        else:
            return None, "Another Git backup is already running."

    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(str(os.getpid()))
        return lock_path, ""
    except OSError as exc:
        return None, f"Could not create application backup lock: {exc}"


def release_app_lock(lock_path):
    if not lock_path:
        return
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


def clean_git_lock(lock_path, force_unlock):
    if not lock_path.exists():
        return True, ""

    print(f"Found Git lock file: {lock_path}")
    age = lock_age_seconds(lock_path)
    should_delete = age > GIT_LOCK_STALE_SECONDS or force_unlock
    if not should_delete:
        return False, f"{lock_path.name} exists and is not stale yet"

    try:
        lock_path.unlink()
        if age > GIT_LOCK_STALE_SECONDS:
            print(f"Removed stale {lock_path.name}")
        else:
            print(f"Removed {lock_path.name}")
        return True, ""
    except OSError:
        message = f"{lock_path.name} is locked by another process or permission issue"
        print(message)
        print_permission_help()
        return False, message


def clean_git_locks(repo_path, force_unlock):
    for lock_name in ["index.lock", "packed-refs.lock"]:
        lock_ok, lock_error = clean_git_lock(repo_path / ".git" / lock_name, force_unlock)
        if not lock_ok:
            return False, lock_error
    return True, ""


def get_commit_hash(repo_path):
    result = run_command(["git", "rev-parse", "HEAD"], repo_path)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Create a safe Git backup commit and push.")
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="Commit message.")
    parser.add_argument("--force-unlock", action="store_true", help="Try to remove Git lock files before backup.")
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
    app_lock_path = None

    print(f"Repo: {repo_path}")
    print(f"Branch: {branch or '(detached or unknown)'}")
    print(f"Remote origin: {remote or '(missing)'}")

    if not branch:
        error = branch_error or "Current branch could not be detected."
        print(f"Error: {error}")
        return 1

    app_lock_path, app_lock_error = acquire_app_lock(repo_path)
    if not app_lock_path:
        print(f"Branch: {branch}")
        print(f"Commit hash: {commit_hash or 'none'}")
        print("Push status: failed")
        print(f"Error: {app_lock_error}")
        return 1

    lock_ok, lock_error = clean_git_locks(repo_path, args.force_unlock)
    if not lock_ok:
        release_app_lock(app_lock_path)
        print(f"Branch: {branch}")
        print(f"Commit hash: {commit_hash or 'none'}")
        print(f"Push status: failed")
        print(f"Error: {lock_error}")
        return 1

    try:
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
    finally:
        release_app_lock(app_lock_path)


if __name__ == "__main__":
    sys.exit(main())
