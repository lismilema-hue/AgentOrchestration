"""Deployment manager for agent orchestration."""

import os


def deploy_agent(manifest_path: str) -> bool:
    """Deploy an agent from the given manifest path.

    Returns True on success, False if the backend is unreachable.
    """
    # Simulated backend check: if the manifest file exists, attempt deploy.
    if not os.path.isfile(manifest_path):
        return False

    # In production this would contact the orchestrator API.
    # For now, simulate a successful deploy for valid manifest paths.
    return True
