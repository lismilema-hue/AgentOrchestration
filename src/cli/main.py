"""CLI entry point for the agent orchestrator."""

import argparse
import sys

from src.common.config import Config
from src.common.logging import configure_logging
from src.deploy.manager import deploy_agent


def non_negative_int(value):
    """Argparse type: ensure the value is a non-negative integer."""
    try:
        ivalue = int(value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer")
    if ivalue < 0:
        raise argparse.ArgumentTypeError(f"'{value}' is negative; tail must be zero or a positive integer")
    return ivalue


def handle_init(args) -> int:
    """Initialize a new project. Returns exit code 0 on success."""
    print(f"Initializing project: {args.name}")
    return 0


def handle_deploy(args) -> int:
    """Deploy an agent from a manifest file. Returns 0 on success, 1 on failure."""
    print(f"Deploying agent from manifest: {args.manifest}")
    if deploy_agent(args.manifest):
        print("Deploy succeeded.")
        return 0
    else:
        print("Deploy failed: backend unreachable or manifest not found.", file=sys.stderr)
        return 1


def handle_status(args) -> int:
    """Show agent status. Returns exit code 0."""
    print("Checking agent status...")
    return 0


def handle_logs(args) -> int:
    """View agent logs. Returns exit code 0."""
    print(f"Fetching logs for agent: {args.agent_id}")
    return 0


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

    if args.verbose:
        configure_logging("DEBUG")
    else:
        configure_logging("INFO")

    handler_map = {
        "init": handle_init,
        "deploy": handle_deploy,
        "status": handle_status,
        "logs": handle_logs,
    }

    handler = handler_map.get(args.command)
    if handler is not None:
        exit_code = handler(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
