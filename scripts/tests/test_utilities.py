import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

UTILITIES = [
    "wait-for-healthy.sh",
    "start_all.sh",
    "stop_all.sh",
    "restart_all.sh",
    "status_all.sh",
    "logs_all.sh",
    "apply-migrations.sh",
    "reset_all.sh",
]


def test_utility_scripts_exist():
    for name in UTILITIES:
        path = SCRIPTS_DIR / name
        assert path.exists(), f"Missing utility script: {path}"


def test_utility_scripts_are_executable():
    for name in UTILITIES:
        path = SCRIPTS_DIR / name
        assert path.stat().st_mode & 0o111, f"Script is not executable: {path}"


def test_utility_scripts_have_valid_bash_syntax():
    for name in UTILITIES:
        path = SCRIPTS_DIR / name
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in {path}: {result.stderr}"
