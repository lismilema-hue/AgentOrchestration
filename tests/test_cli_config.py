"""Tests for CLI config path resolution (tilde expansion, relative path resolution)."""

import os
from pathlib import Path
from src.cli.main import resolve_config_path


class TestResolveConfigPath:
    def test_none_path_returns_none(self):
        """Passing None should return None."""
        assert resolve_config_path(None) is None

    def test_tilde_path_expands_to_home(self):
        """A path starting with ~ should expand to the user's home directory."""
        home = str(Path.home())
        result = resolve_config_path("~/ao/config.json")
        assert result.startswith(home), f"Expected {result!r} to start with {home!r}"
        assert "~" not in result, f"Tilde found in resolved path: {result!r}"
        assert result.endswith("ao/config.json")

    def test_absolute_path_unchanged(self):
        """An absolute path without tilde should remain unchanged (modulo resolution)."""
        path = "/etc/ao/config.json"
        result = resolve_config_path(path)
        assert result == path

    def test_relative_path_resolved(self):
        """A relative path should be resolved to an absolute path."""
        result = resolve_config_path("config.json")
        assert result == str(Path("config.json").resolve()), f"Unexpected: {result!r}"

    def test_tilde_user_path_preserved(self):
        """A ~user path should expand to that user's home."""
        result = resolve_config_path("~root/ao/config.json")
        # We just verify it doesn't contain literal tilde and has resolved form
        assert "~" not in result, f"Tilde found in resolved path: {result!r}"
        assert result.endswith("ao/config.json")

    def test_empty_string_path(self, tmp_path):
        """An empty string config path should resolve to CWD."""
        cwd = Path.cwd()
        result = resolve_config_path("")
        assert result == str(cwd.resolve())
