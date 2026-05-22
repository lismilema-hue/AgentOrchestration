"""Tests for the SDK agent metadata API."""

import pytest
from src.sdk.agent import BaseAgent


class StubAgent(BaseAgent):
    """Concrete stub for testing abstract BaseAgent."""

    async def setup(self) -> None:
        pass

    async def handle_task(self, task: dict) -> None:
        pass

    async def cleanup(self) -> None:
        pass


class TestBaseAgentMetadata:
    def test_set_metadata_valid_key(self):
        agent = StubAgent("test-id", "test-agent")
        agent.set_metadata("env", "prod")
        assert agent.get_metadata("env") == "prod"

    def test_set_metadata_empty_key_raises(self):
        agent = StubAgent("test-id", "test-agent")
        with pytest.raises(ValueError, match="non-empty string"):
            agent.set_metadata("", "value")

    def test_set_metadata_whitespace_key_raises(self):
        agent = StubAgent("test-id", "test-agent")
        with pytest.raises(ValueError, match="non-empty string"):
            agent.set_metadata("   ", "value")

    def test_set_metadata_non_string_key_raises(self):
        agent = StubAgent("test-id", "test-agent")
        with pytest.raises(ValueError, match="non-empty string"):
            agent.set_metadata(123, "value")  # type: ignore[arg-type]

    def test_set_metadata_trims_key(self):
        agent = StubAgent("test-id", "test-agent")
        agent.set_metadata("  env  ", "prod")
        assert agent.get_metadata("env") == "prod"
        assert agent.get_metadata("  env  ") is None
