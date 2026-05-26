import pytest
from src.common.metrics import MetricsCollector, MetricNamePolicy, _default_sanitizer


class TestMetricsCollector:
    def setup_method(self):
        self.metrics = MetricsCollector()

    def test_increment(self):
        self.metrics.increment("requests.total")
        self.metrics.increment("requests.total")
        snapshot = self.metrics.snapshot()
        assert snapshot["counters"]["requests.total"] == 2

    def test_gauge(self):
        self.metrics.gauge("memory.usage", 85.5)
        snapshot = self.metrics.snapshot()
        assert snapshot["gauges"]["memory.usage"] == 85.5

    def test_gauge_rejects_non_numeric(self):
        with pytest.raises(TypeError, match="Gauge value must be numeric"):
            self.metrics.gauge("test", "not_a_number")
        with pytest.raises(TypeError, match="Gauge value must be numeric"):
            self.metrics.gauge("test", None)
        # Numeric types should still work
        self.metrics.gauge("int_val", 42)
        self.metrics.gauge("float_val", 3.14)
        snapshot = self.metrics.snapshot()
        assert snapshot["gauges"]["int_val"] == 42
        assert snapshot["gauges"]["float_val"] == 3.14

    def test_observe(self):
        self.metrics.observe("response.time", 0.5)
        self.metrics.observe("response.time", 1.5)
        snapshot = self.metrics.snapshot()
        assert snapshot["histograms"]["response.time"]["count"] == 2
        assert snapshot["histograms"]["response.time"]["avg"] == 1.0

    def test_timer(self):
        self.metrics.start_timer("operation")
        import time
        time.sleep(0.01)
        duration = self.metrics.stop_timer("operation")
        assert duration > 0.005

    # --- Metric name sanitization tests ---

    def test_valid_metric_names_accepted(self):
        """Valid names should pass through without error."""
        for name in ["requests.total", "memory_usage", "cpu-usage", "a", "_private"]:
            self.metrics.increment(name)
        snapshot = self.metrics.snapshot()
        for name in ["requests.total", "memory_usage", "cpu-usage", "a", "_private"]:
            assert name in snapshot["counters"], f"{name!r} should be in counters"

    def test_invalid_metric_names_rejected_with_strict_policy(self):
        """With strict validation, invalid names raise ValueError."""
        for bad_name in [
            "123starts_with_digit",
            "has spaces",
            "has/slash",
            "has@symbol",
            "",
        ]:
            with pytest.raises(ValueError, match="Metric name.*does not match"):
                self.metrics.increment(bad_name)

    def test_sanitizer_replaces_invalid_chars(self):
        """With a sanitizer policy, invalid characters are replaced."""
        policy = MetricNamePolicy(sanitizer=_default_sanitizer)
        collector = MetricsCollector(name_policy=policy)

        collector.increment("staging.requests.total")
        collector.gauge("prod/memory/usage", 75.0)
        collector.observe("response time (ms)", 0.5)
        collector.increment("123bad")

        snapshot = collector.snapshot()
        assert "staging.requests.total" in snapshot["counters"]
        assert "prod_memory_usage" in snapshot["gauges"]
        assert "response_time__ms_" in snapshot["histograms"]
        assert "_123bad" in snapshot["counters"]

    def test_sanitizer_blocks_env_identifiers(self):
        """Custom sanitizer can strip environment identifiers from metric names."""
        def strip_env(name: str) -> str:
            import re
            # Remove common environment identifiers like env-*, staging.*, prod-
            name = re.sub(r"^(env-|staging[._-]|prod[._-]|dev[._-])", "", name)
            # Then sanitize any remaining invalid chars
            return _default_sanitizer(name)

        policy = MetricNamePolicy(sanitizer=strip_env)
        collector = MetricsCollector(name_policy=policy)

        collector.increment("staging.requests.total")
        collector.increment("prod-memory.usage")
        collector.increment("env-queue.size")
        collector.increment("dev.api.calls")

        snapshot = collector.snapshot()
        # Sanitized names should not retain environment prefixes
        assert "staging.requests.total" not in snapshot["counters"]
        assert "requests.total" in snapshot["counters"]
        assert "memory.usage" in snapshot["counters"]
        assert "queue.size" in snapshot["counters"]
        assert "api.calls" in snapshot["counters"]

    def test_default_sanitizer_edge_cases(self):
        """Test _default_sanitizer on edge-case inputs."""
        assert _default_sanitizer("valid_name") == "valid_name"
        assert _default_sanitizer("") == "_metric"
        assert _default_sanitizer("!!!") == "_metric"
        assert _default_sanitizer("123abc") == "_123abc"
        assert _default_sanitizer("a.b-c_d") == "a.b-c_d"
        assert _default_sanitizer(" space ") == "_space_"

    def test_name_policy_swappable(self):
        """The name_policy property should be swappable at runtime."""
        collector = MetricsCollector()
        with pytest.raises(ValueError, match="Metric name"):
            collector.increment("has space")

        policy = MetricNamePolicy(sanitizer=_default_sanitizer)
        collector.name_policy = policy
        collector.increment("has space")
        snapshot = collector.snapshot()
        assert "has space" not in snapshot["counters"]
        assert "has_space" in snapshot["counters"]
