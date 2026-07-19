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