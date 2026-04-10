"""PROMEOS — Enedis SGE pipeline configuration.

Externalized settings for the ingestion pipeline (SF4).
"""

import os
from pathlib import Path

# Max retries on a file in ERROR status (4 total attempts: 1 initial + 3 retries).
# Beyond this limit the file transitions to PERMANENTLY_FAILED.
MAX_RETRIES: int = 3


def get_flux_dir(override: str | None = None) -> Path:
    """Resolve the Enedis flux directory.

    Priority: override > env var ENEDIS_FLUX_DIR.
    No fallback — ENEDIS_FLUX_DIR is required if no override is provided.

    Args:
        override: Explicit directory path (from CLI --dir or API body).

    Returns:
        Path to the flux directory.

    Raises:
        ValueError: If no directory is configured or the path is not a directory.
    """
    if override and override.strip():
        path = Path(override)
    else:
        env_value = os.environ.get("ENEDIS_FLUX_DIR")
        if not env_value:
            raise ValueError("ENEDIS_FLUX_DIR environment variable is required — set it in .env")
        path = Path(env_value)

    if not path.is_dir():
        raise ValueError(f"{path} is not a directory")

    return path
