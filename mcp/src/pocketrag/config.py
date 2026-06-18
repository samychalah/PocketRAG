"""Centralized configuration loading from config.yaml with environment variable overrides.

This module defines the configuration schema and loading logic for the NotebookLM client.
Configuration values are resolved using the following order of precedence:
1. Environment variables (in UPPERCASE format, e.g., NBLM_CONFIG, PROJECT_NUMBER).
2. YAML configuration file (path defined by `NBLM_CONFIG` env var, defaults to `config.yaml`).
3. Default fallback values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# The path to the configuration file, customizable via environment variable.
_CONFIG_PATH = os.environ.get("NBLM_CONFIG", "config.yaml")


def _load_yaml() -> dict[str, Any]:
    """Load and parse the YAML configuration file if it exists.

    Returns:
        A dictionary containing the parsed YAML configuration, or an empty dictionary
        if the file does not exist or is empty.
    """
    path = Path(_CONFIG_PATH)
    if path.exists():
        with path.open() as f:
            return yaml.safe_load(f) or {}
    return {}


def _get(data: dict, key: str, default: Any = None) -> Any:
    """Resolve a configuration value, prioritizing environment variables over YAML.

    Args:
        data: The dictionary loaded from the YAML configuration file.
        key: The configuration key (e.g., "project_number").
        default: The default value to return if the key is not found in either source.

    Returns:
        The resolved value. If an environment variable matching the uppercase key
        (e.g. "PROJECT_NUMBER") is set, its value is returned. Otherwise, the value
        from the YAML dictionary is returned, falling back to the default.
    """
    env_val = os.environ.get(key.upper())
    if env_val is not None:
        return env_val
    return data.get(key, default)


def _as_bool(val: Any) -> bool:
    """Coerce a value to a boolean, supporting common truthy string representations.

    Args:
        val: The value to coerce.

    Returns:
        True if the value represents a truthy state ("1", "true", "yes", "on" case-insensitive),
        False otherwise.
    """
    return str(val).lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    """Configuration settings for the NotebookLMClient.

    Attributes:
        project_number: The Google Cloud Project Number (numeric ID) containing the
            Discovery Engine resources. Note: This must be the project number, not the project ID.
        location: The GCP region/location where the Discovery Engine resources reside (e.g., "us").
        api_version: The target API version of the Discovery Engine service (e.g., "v1").
        mock_mode: If True, the client operates in an offline mock mode using an in-memory store,
            bypassing all live GCP API calls. Useful for local development and testing.
        poll_initial_seconds: Initial backoff duration in seconds when polling long-running operations.
        poll_max_seconds: Maximum backoff duration in seconds when polling long-running operations.
        poll_timeout_seconds: Maximum total duration in seconds to wait for a long-running operation before timing out.
        retry_max_attempts: Maximum number of retry attempts for transient API errors (e.g., rate limits).
    """
    project_number: str
    location: str
    api_version: str
    mock_mode: bool
    poll_initial_seconds: float
    poll_max_seconds: float
    poll_timeout_seconds: float
    retry_max_attempts: int

    @classmethod
    def load(cls) -> "Config":
        """Load and resolve the configuration from the YAML file and environment variables.

        Returns:
            An initialized Config instance with resolved values.
        """
        d = _load_yaml()
        return cls(
            project_number=str(_get(d, "project_number", "0")),
            location=str(_get(d, "location", "us")),
            api_version=str(_get(d, "api_version", "v1")),
            mock_mode=_as_bool(_get(d, "mock_mode", True)),
            poll_initial_seconds=float(_get(d, "poll_initial_seconds", 2)),
            poll_max_seconds=float(_get(d, "poll_max_seconds", 15)),
            poll_timeout_seconds=float(_get(d, "poll_timeout_seconds", 300)),
            retry_max_attempts=int(_get(d, "retry_max_attempts", 3)),
        )
