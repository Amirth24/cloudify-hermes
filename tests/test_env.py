"""Tests for cloudify_hermes/env.py — CloudifyEnv central env-var config."""

from __future__ import annotations

import os

import pytest

from cloudify_hermes.env import CloudifyEnv


class TestCloudifyEnvDefaults:
    """All env vars absent → defaults are used."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "CLOUDIFY_OV_ENDPOINT",
            "CLOUDIFY_S3_PREFIX",
            "CLOUDIFY_S3_REGION",
            "CLOUDIFY_S3_SESSION_NAME",
            "CLOUDIFY_AGENT_ID",
            "CLOUDIFY_PASSPHRASE_ENV",
            "CLOUDIFY_MEM0_API_KEY_ENV",
        ):
            monkeypatch.delenv(var, raising=False)

    def test_defaults(self) -> None:
        cfg = CloudifyEnv()
        assert cfg.ov_endpoint == "http://localhost:8765"
        assert cfg.s3_prefix == "cloudify/"
        assert cfg.s3_region == "ap-south-1"
        assert cfg.s3_session_name == "cloudify-hermes"
        assert cfg.agent_id == "hermes"
        assert cfg.passphrase_env == "CLOUDIFY_PASSPHRASE"
        assert cfg.mem0_api_key_env == "MEM0_API_KEY"


class TestCloudifyEnvOverrides:
    """All env vars set → overrides are used."""

    @pytest.fixture(autouse=True)
    def _set_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLOUDIFY_OV_ENDPOINT", "https://ov.example.com")
        monkeypatch.setenv("CLOUDIFY_S3_PREFIX", "my-prefix/")
        monkeypatch.setenv("CLOUDIFY_S3_REGION", "us-east-1")
        monkeypatch.setenv("CLOUDIFY_S3_SESSION_NAME", "my-session")
        monkeypatch.setenv("CLOUDIFY_AGENT_ID", "my-agent")
        monkeypatch.setenv("CLOUDIFY_PASSPHRASE_ENV", "MY_PASSPHRASE")
        monkeypatch.setenv("CLOUDIFY_MEM0_API_KEY_ENV", "MY_MEM0_KEY")

    def test_overrides(self) -> None:
        cfg = CloudifyEnv()
        assert cfg.ov_endpoint == "https://ov.example.com"
        assert cfg.s3_prefix == "my-prefix/"
        assert cfg.s3_region == "us-east-1"
        assert cfg.s3_session_name == "my-session"
        assert cfg.agent_id == "my-agent"
        assert cfg.passphrase_env == "MY_PASSPHRASE"
        assert cfg.mem0_api_key_env == "MY_MEM0_KEY"
