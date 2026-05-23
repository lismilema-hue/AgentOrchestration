"""Tests for the SDK client module."""

import pytest
from src.sdk.client import OrchestratorClient


class TestOrchestratorClient:
    def setup_method(self):
        self.client = OrchestratorClient(
            base_url="http://test.local",
            api_key="test-key",
        )

    def test_register_agent_blank_name_raises(self):
        """Blank agent names should be rejected with ValueError."""
        with pytest.raises(ValueError, match="agent name must not be blank"):
            self.client.register_agent("", "worker.processor")

    def test_register_agent_whitespace_name_raises(self):
        """Whitespace-only agent names should be rejected with ValueError."""
        with pytest.raises(ValueError, match="agent name must not be blank"):
            self.client.register_agent("   ", "worker.processor")

    def test_register_agent_valid_name_passes(self):
        """Valid agent names should proceed to the request layer."""
        result = self.client.register_agent("my-agent", "worker.processor")
        # Without a real server, _request returns an error dict.
        # The key assertion is that no ValueError is raised.
        assert isinstance(result, dict)
