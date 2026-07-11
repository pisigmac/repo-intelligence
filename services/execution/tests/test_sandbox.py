import pytest
from unittest.mock import patch, MagicMock
from services.execution.main import StepExecutor

@patch("docker.from_env")
def test_sandbox_run_tests_docker_success(mock_from_env):
    # Mocking Docker client
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    mock_container_run = mock_client.containers.run
    mock_container_run.return_value = b"All tests passed!"

    executor = StepExecutor("/data/repos/test-repo")
    status, output = executor._handle_run_tests("/data/repos/test-repo", {"command": "npm test"})
    
    assert status == "completed"
    assert "Tests passed (Sandboxed)" in output
    assert "All tests passed!" in output
    
    mock_container_run.assert_called_once()
    kwargs = mock_container_run.call_args[1]
    assert kwargs["image"] == "node:18-alpine"
    assert kwargs["command"] == ["sh", "-c", "npm test"]
    assert "repo-intelligence_repo_storage" in kwargs["volumes"]
    assert kwargs["remove"] is True

@patch("docker.from_env")
def test_sandbox_run_tests_docker_failure(mock_from_env):
    import docker
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    # Simulate a Docker container failure (e.g., test fails)
    class FakeContainerError(docker.errors.ContainerError):
        def __init__(self):
            self.stderr = b"Tests failed!"
            self.stdout = b""
            
    mock_client.containers.run.side_effect = FakeContainerError()

    executor = StepExecutor("/data/repos/test-repo")
    status, output = executor._handle_run_tests("/data/repos/test-repo", {"command": "npm test"})
    
    assert status == "failed"
    assert "Tests failed (Sandboxed)" in output
    assert "Tests failed!" in output

@patch("subprocess.run")
def test_sandbox_run_tests_fallback(mock_subprocess_run):
    # Simulate docker not installed/importable
    with patch.dict('sys.modules', {'docker': None}):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Local tests passed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        executor = StepExecutor("/data/repos/test-repo")
        status, output = executor._handle_run_tests("/data/repos/test-repo", {"command": "npm test"})
        
        assert status == "completed"
        assert "Tests passed\nLocal tests passed" in output
        mock_subprocess_run.assert_called_once()

@patch("os.path.isfile")
@patch("docker.from_env")
def test_sandbox_validate_syntax_docker_success(mock_from_env, mock_isfile):
    mock_isfile.return_value = True
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    
    mock_client.containers.run.return_value = b""

    executor = StepExecutor("/data/repos/test-repo")
    status, output = executor._handle_validate_syntax("/data/repos/test-repo/app.js", {})
    
    assert status == "completed"
    assert "Syntax valid (Sandboxed)" in output
    
    kwargs = mock_client.containers.run.call_args[1]
    assert kwargs["network_mode"] == "none"  # Crucial for sandbox isolation
    assert kwargs["working_dir"] == "/data/repos/test-repo"
    assert kwargs["command"] == ["sh", "-c", "node --check app.js"]
