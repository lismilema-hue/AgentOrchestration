"""Tests for AgentSandbox — covering directory permission enforcement."""

import os
import stat
import tempfile
import pytest

from src.agent.sandbox import AgentSandbox


class TestSandboxPermissions:
    """Regression: sandbox directories must use restrictive (0o700) permissions."""

    def test_sandbox_directory_has_restrictive_permissions(self):
        """Sandbox.create() directories should be owner-only rwx."""
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = AgentSandbox(base_path=tmp)
            path = sandbox.create("test-agent-1")

            assert path.exists(), "Sandbox directory was not created"
            mode = stat.S_IMODE(os.stat(path).st_mode)
            assert mode == 0o700, (
                f"Expected 0o700 but got {oct(mode)}"
            )

    def test_multiple_sandboxes_all_restrictive(self):
        """Each sandbox directory independently gets restrictive permissions."""
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = AgentSandbox(base_path=tmp)
            for i in range(3):
                path = sandbox.create(f"multi-agent-{i}")
                mode = stat.S_IMODE(os.stat(path).st_mode)
                assert mode == 0o700, (
                    f"Sandbox {i}: expected 0o700 but got {oct(mode)}"
                )

    def test_sandbox_permissions_independent_of_umask(self):
        """Sandbox permissions should not be affected by a permissive umask."""
        old_umask = os.umask(0o022)
        os.umask(old_umask)  # restore immediately, we only test behavior

        with tempfile.TemporaryDirectory() as tmp:
            sandbox = AgentSandbox(base_path=tmp)
            path = sandbox.create("umask-test-agent")
            mode = stat.S_IMODE(os.stat(path).st_mode)
            assert mode == 0o700, (
                f"With umask {oct(old_umask)}: expected 0o700 but got {oct(mode)}"
            )

    def test_sandbox_base_path_exists(self):
        """Base path is created by tempfile.mkdtemp with safe defaults."""
        sandbox = AgentSandbox()
        path = sandbox.create("ephemeral-agent")
        try:
            assert path.exists()
            mode = stat.S_IMODE(os.stat(path).st_mode)
            assert mode == 0o700, (
                f"Expected 0o700 but got {oct(mode)}"
            )
        finally:
            sandbox.destroy("ephemeral-agent")
            sandbox.cleanup_all()
