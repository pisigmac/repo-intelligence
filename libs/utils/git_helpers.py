"""Git repository cloning and inspection utilities."""
import os
import re
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def clone_repository(
    git_url: str,
    dest_path: str,
    branch: str = "main",
    auth_token: Optional[str] = None,
) -> str:
    """Clone a git repository to dest_path. Returns the commit hash."""
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    os.makedirs(dest_path, exist_ok=True)

    # Inject auth token into URL if provided
    clone_url = git_url
    if auth_token and git_url.startswith("https://"):
        clone_url = git_url.replace("https://", f"https://{auth_token}@")

    cmd = ["git", "clone", "--depth", "1", "--branch", branch, clone_url, dest_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    # Get commit hash
    result = subprocess.run(
        ["git", "-C", dest_path, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    commit_hash = result.stdout.strip()
    logger.info("Repository cloned", extra={"url": git_url, "commit": commit_hash, "path": dest_path})
    return commit_hash


def get_repo_files(repo_path: str, extensions: Optional[list[str]] = None) -> list[Path]:
    """List all files in repo, optionally filtered by extension."""
    repo = Path(repo_path)
    files = []
    for f in repo.rglob("*"):
        if f.is_file() and ".git" not in str(f):
            if extensions is None or f.suffix in extensions:
                files.append(f)
    return files


def read_file_safe(file_path: Path, max_bytes: int = 1_000_000) -> Optional[str]:
    """Read a file safely, skipping binary files."""
    try:
        stat = file_path.stat()
        if stat.st_size > max_bytes:
            return None
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Simple binary check
        if "\0" in content:
            return None
        return content
    except Exception as e:
        logger.warning("Failed to read file", extra={"path": str(file_path), "error": str(e)})
        return None
