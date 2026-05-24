"""Tests for CLI deploy command exit code propagation."""

import os
import sys
import tempfile
import pytest

from src.cli.main import handle_deploy, handle_init, handle_status, handle_logs


class TestDeployExitCodes:
    """Verify that deploy failure propagates a non-zero exit code."""

    def test_deploy_success_returns_zero(self):
        """A valid manifest file should result in exit code 0."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            manifest_path = f.name
            f.write(b"agent: test\n")

        try:
            from argparse import Namespace
            args = Namespace(manifest=manifest_path)
            assert handle_deploy(args) == 0
        finally:
            os.unlink(manifest_path)

    def test_deploy_missing_manifest_returns_one(self):
        """A non-existent manifest file should result in exit code 1."""
        from argparse import Namespace
        args = Namespace(manifest="/tmp/nonexistent_manifest_xyz.yaml")
        assert handle_deploy(args) == 1


class TestHandlerExitCodes:
    """Verify that all command handlers return the expected exit codes."""

    def test_init_returns_zero(self):
        from argparse import Namespace
        args = Namespace(name="test_project")
        assert handle_init(args) == 0

    def test_status_returns_zero(self):
        from argparse import Namespace
        args = Namespace(watch=False)
        assert handle_status(args) == 0

    def test_logs_returns_zero(self):
        from argparse import Namespace
        args = Namespace(agent_id="agent-123", tail=50)
        assert handle_logs(args) == 0
