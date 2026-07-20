"""Central env-var configuration for cloudify-hermes.

Usage::

    from cloudify_hermes.env import CloudifyEnv

    cfg = CloudifyEnv()
    print(cfg.ov_endpoint)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CloudifyEnv:
    """Read-only configuration sourced from environment variables.

    Every field uses ``field(default_factory=...)`` so defaults are
    evaluated at instantiation time, not at import time.  This lets
    tests monkeypatch ``os.environ`` before constructing the object.
    """

    # ── OpenVoice endpoint ──────────────────────────────────────────
    ov_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_OV_ENDPOINT", "http://localhost:8765"
        )
    )

    # ── S3 / object-store settings ──────────────────────────────────
    s3_prefix: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_S3_PREFIX", "cloudify/"
        )
    )

    s3_region: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_S3_REGION", "ap-south-1"
        )
    )

    s3_session_name: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_S3_SESSION_NAME", "cloudify-hermes"
        )
    )

    # ── Agent identity ──────────────────────────────────────────────
    agent_id: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_AGENT_ID", "hermes"
        )
    )

    # ── Secret / key env-var names (not the values themselves) ──────
    passphrase_env: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_PASSPHRASE_ENV", "CLOUDIFY_PASSPHRASE"
        )
    )

    mem0_api_key_env: str = field(
        default_factory=lambda: os.environ.get(
            "CLOUDIFY_MEM0_API_KEY_ENV", "MEM0_API_KEY"
        )
    )
