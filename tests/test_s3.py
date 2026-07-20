from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from cloudify_hermes.storage.s3 import S3Backend


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_upload(mock_boto3):
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session
    backend = S3Backend(bucket="test-bucket", prefix="cloudify/", region="ap-south-1", profile="")
    backend.put("skills/test-skill/SKILL.md", b"content")
    mock_client.put_object.assert_called_once()
    args = mock_client.put_object.call_args
    assert args[1]["Bucket"] == "test-bucket"
    assert args[1]["Key"] == "cloudify/skills/test-skill/SKILL.md"
    assert args[1]["Body"] == b"content"


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_download(mock_boto3):
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session
    mock_client.get_object.return_value = {"Body": MagicMock(read=lambda: b"content")}
    backend = S3Backend(bucket="test-bucket", prefix="cloudify/", region="ap-south-1", profile="")
    data = backend.get("skills/test-skill/SKILL.md")
    assert data == b"content"


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_list(mock_boto3):
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "cloudify/skills/a/SKILL.md"}, {"Key": "cloudify/skills/b/SKILL.md"}]
    }
    backend = S3Backend(bucket="test-bucket", prefix="cloudify/", region="ap-south-1", profile="")
    keys = backend.list("skills/")
    assert len(keys) == 2
    assert "cloudify/skills/a/SKILL.md" in keys


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_delete(mock_boto3):
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session
    backend = S3Backend(bucket="test-bucket", prefix="cloudify/", region="ap-south-1", profile="")
    backend.delete("skills/test-skill/SKILL.md")
    mock_client.delete_object.assert_called_once()


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_get_returns_none_on_nosuchkey(mock_boto3):
    from botocore.exceptions import ClientError
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session
    mock_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )
    backend = S3Backend(bucket="test-bucket", prefix="cloudify/", region="ap-south-1", profile="")
    data = backend.get("nonexistent")
    assert data is None


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_role_assumption(mock_boto3):
    """Test that S3Backend assumes an IAM role when role_arn is provided."""
    mock_session = MagicMock()
    mock_boto3.Session.return_value = mock_session

    # STS client returns assumed role credentials
    mock_sts = MagicMock()
    mock_s3_client = MagicMock()
    mock_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIA-TEST",
            "SecretAccessKey": "secret-test",
            "SessionToken": "session-token-test",
        }
    }
    # First .client("sts") call returns STS, second .client("s3") returns S3
    mock_session.client.side_effect = [mock_sts, mock_s3_client]

    backend = S3Backend(
        bucket="test-bucket",
        prefix="cloudify/",
        region="ap-south-1",
        profile="",
        role_arn="arn:aws:iam::123456789012:role/CloudifyBackupRole",
    )

    # Verify STS assume_role was called with the right args
    mock_sts.assume_role.assert_called_once()
    call_args = mock_sts.assume_role.call_args[1]
    assert call_args["RoleArn"] == "arn:aws:iam::123456789012:role/CloudifyBackupRole"
    assert call_args["RoleSessionName"] == "cloudify-hermes"

    # Verify S3 client was created with assumed credentials
    mock_boto3.client.assert_called_with(
        "s3",
        region_name="ap-south-1",
        aws_access_key_id="ASIA-TEST",
        aws_secret_access_key="secret-test",
        aws_session_token="session-token-test",
    )


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_role_assumption_with_external_id(mock_boto3):
    """Test that external_id is passed to assume_role when provided."""
    mock_session = MagicMock()
    mock_boto3.Session.return_value = mock_session
    mock_sts = MagicMock()
    mock_s3_client = MagicMock()
    mock_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIA-TEST",
            "SecretAccessKey": "secret-test",
            "SessionToken": "session-token-test",
        }
    }
    mock_session.client.side_effect = [mock_sts, mock_s3_client]

    backend = S3Backend(
        bucket="test-bucket",
        role_arn="arn:aws:iam::123456789012:role/CloudifyBackupRole",
        external_id="my-external-id",
    )
    call_args = mock_sts.assume_role.call_args[1]
    assert call_args["ExternalId"] == "my-external-id"


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_no_role_uses_default_credentials(mock_boto3):
    """Test that without role_arn, boto3 uses default session credentials."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session

    backend = S3Backend(
        bucket="test-bucket",
        prefix="cloudify/",
        region="ap-south-1",
        profile="gld",
    )
    # Should call session.client("s3") directly, not STS
    mock_session.client.assert_called_with("s3")


@patch("cloudify_hermes.storage.s3.boto3")
def test_s3_defaults_from_env(mock_boto3, monkeypatch):
    """Test that S3Backend uses CloudifyEnv defaults when args are not provided."""
    monkeypatch.setenv("CLOUDIFY_S3_PREFIX", "env-prefix/")
    monkeypatch.setenv("CLOUDIFY_S3_REGION", "eu-west-1")

    # Re-create the module-level _env so it picks up the monkeypatched env vars
    from cloudify_hermes.env import CloudifyEnv
    import cloudify_hermes.storage.s3 as s3_module
    s3_module._env = CloudifyEnv()

    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3.Session.return_value = mock_session

    backend = S3Backend(bucket="test-bucket")

    # Verify boto3.Session was called with the env region
    mock_boto3.Session.assert_called_once_with(region_name="eu-west-1")
    # Verify prefix came from env
    assert backend.prefix == "env-prefix/"
