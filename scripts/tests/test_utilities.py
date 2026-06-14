import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

yaml = pytest.importorskip("yaml", reason="PyYAML not installed")

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


def test_analysis_and_capability_services_share_repo_storage():
    """Services that exchange filesystem paths must share the repo_storage volume."""
    with COMPOSE_FILE.open() as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    required_services = ["analysis-service", "capability-service"]

    for svc_name in required_services:
        svc = services.get(svc_name, {})
        env = svc.get("environment", [])
        env_dict = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                env_dict[key] = value
            elif isinstance(item, dict):
                env_dict.update(item)

        volumes = svc.get("volumes", [])
        volume_names = [v.split(":")[0] for v in volumes if isinstance(v, str)]

        assert env_dict.get("REPO_STORAGE_PATH") == "/data/repos", (
            f"{svc_name} must set REPO_STORAGE_PATH=/data/repos"
        )
        assert "repo_storage" in volume_names, (
            f"{svc_name} must mount the repo_storage volume"
        )
