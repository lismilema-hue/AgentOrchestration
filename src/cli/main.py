"""CLI entry point for the agent orchestrator."""

import argparse
import sys
from pathlib import Path

from src.common.config import Config
from src.common.logging import configure_logging


def non_negative_int(value):
    """Argparse type: ensure the value is a non-negative integer."""
    try:
        ivalue = int(value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer")
    if ivalue < 0:
        raise argparse.ArgumentTypeError(f"'{value}' is negative; tail must be zero or a positive integer")
    return ivalue


def resolve_config_path(config_path: str | None) -> str | None:
    """Expand user home (~) and resolve relative paths in a config path."""
    if config_path is None:
        return None
    return str(Path(config_path).expanduser().resolve())


def cli():
    parser = argparse.ArgumentParser(description="Agent Orchestrator CLI")
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", help="Project name")

    deploy_parser = subparsers.add_parser("deploy", help="Deploy an agent")
    deploy_parser.add_argument("manifest", help="Path to agent manifest file")

    status_parser = subparsers.add_parser("status", help="Show agent status")
    status_parser.add_argument("--watch", "-w", action="store_true", help="Watch mode")

    logs_parser = subparsers.add_parser("logs", help="View agent logs")
    logs_parser.add_argument("agent_id", help="Agent ID")
    logs_parser.add_argument("--tail", "-t", type=non_negative_int, default=50, help="Number of lines (must be zero or positive)")

    args = parser.parse_args()

    if args.config:
        args.config = resolve_config_path(args.config)

    if args.verbose:
        configure_logging("DEBUG")
    else:
        configure_logging("INFO")

    if args.command == "init":
        print(f"Initializing project: {args.name}")
    elif args.command == "deploy":
        print(f"Deploying agent from manifest: {args.manifest}")
    elif args.command == "status":
        print("Checking agent status...")
    elif args.command == "logs":
        print(f"Fetching logs for agent: {args.agent_id}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
