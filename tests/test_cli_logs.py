"""Tests for CLI argument validation, including non-negative tail check."""

import sys
import pytest
from argparse import ArgumentTypeError
from src.cli.main import non_negative_int


class TestNonNegativeInt:
    def test_positive_int(self):
        assert non_negative_int("10") == 10

    def test_zero(self):
        assert non_negative_int("0") == 0

    def test_negative_raises(self):
        with pytest.raises(ArgumentTypeError, match="negative"):
            non_negative_int("-5")

    def test_non_numeric_raises(self):
        with pytest.raises(ArgumentTypeError, match="not a valid integer"):
            non_negative_int("abc")

    def test_float_string_raises(self):
        with pytest.raises(ArgumentTypeError, match="not a valid integer"):
            non_negative_int("3.14")


class TestLogsTailCli:
    """Integration-style tests that run the CLI and check exit behavior."""

    def test_tail_negative_exits_with_error(self, capsys):
        """A negative --tail value should cause argparse to exit with error."""
        from argparse import ArgumentParser
        p = ArgumentParser()
        p.add_argument("--tail", "-t", type=non_negative_int, default=50)
        with pytest.raises(SystemExit):
            p.parse_args(["--tail", "-5"])

    def test_tail_positive_parses_ok(self):
        """A positive --tail value should parse without error."""
        from argparse import ArgumentParser
        p = ArgumentParser()
        p.add_argument("--tail", "-t", type=non_negative_int, default=50)
        args = p.parse_args(["--tail", "10"])
        assert args.tail == 10

    def test_tail_default_is_fifty(self):
        """When --tail is omitted, the default should be 50."""
        from argparse import ArgumentParser
        p = ArgumentParser()
        p.add_argument("--tail", "-t", type=non_negative_int, default=50)
        args = p.parse_args([])
        assert args.tail == 50
