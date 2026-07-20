"""S3 storage backend with versioning support."""
from __future__ import annotations
import logging
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError
from cloudify_hermes.env import CloudifyEnv

logger = logging.getLogger(__name__)

_env = CloudifyEnv()


class S3Backend:
    def __init__(
        self,
        bucket: str,
        prefix: str | None = None,
        region: str | None = None,
        profile: str = "",
        role_arn: str = "",
        external_id: str = "",
        session_name: str | None = None,
    ):
        self.bucket = bucket
        self.prefix = prefix if prefix is not None else _env.s3_prefix
        region = region if region is not None else _env.s3_region
        session_name = session_name if session_name is not None else _env.s3_session_name

        # Build the base session (profile or default credential chain)
        session_kwargs = {"region_name": region}
        if profile:
            session_kwargs["profile_name"] = profile
        session = boto3.Session(**session_kwargs)

        # If a role ARN is specified, assume it via STS
        if role_arn:
            sts_client = session.client("sts")
            assume_kwargs = {
                "RoleArn": role_arn,
                "RoleSessionName": session_name,
            }
            if external_id:
                assume_kwargs["ExternalId"] = external_id
            assumed = sts_client.assume_role(**assume_kwargs)
            creds = assumed["Credentials"]
            self.client = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
            )
            logger.info("Assumed IAM role: %s (session: %s)", role_arn, session_name)
        else:
            self.client = session.client("s3")

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def put(self, key: str, data: bytes, metadata: Optional[dict] = None) -> str:
        """Upload data to S3. Returns the full S3 key."""
        full_key = self._full_key(key)
        params = {"Bucket": self.bucket, "Key": full_key, "Body": data}
        if metadata:
            params["Metadata"] = {k: str(v) for k, v in metadata.items()}
        self.client.put_object(**params)
        logger.debug("S3 put: %s (%d bytes)", full_key, len(data))
        return full_key

    def get(self, key: str) -> Optional[bytes]:
        """Download data from S3. Returns None if not found."""
        full_key = self._full_key(key)
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=full_key)
            return resp["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def list(self, prefix: str = "") -> List[str]:
        """List keys under a prefix."""
        full_prefix = self._full_key(prefix)
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=full_prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]

    def delete(self, key: str) -> None:
        """Delete an object from S3."""
        full_key = self._full_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=full_key)
        logger.debug("S3 delete: %s", full_key)

    def list_versions(self, key: str) -> List[dict]:
        """List all versions of an object (requires S3 bucket versioning enabled)."""
        full_key = self._full_key(key)
        resp = self.client.list_object_versions(Bucket=self.bucket, Prefix=full_key)
        return [
            {"version_id": v.get("VersionId"), "last_modified": v.get("LastModified"), "size": v.get("Size")}
            for v in resp.get("Versions", [])
        ]

    def get_version(self, key: str, version_id: str) -> Optional[bytes]:
        """Get a specific version of an object."""
        full_key = self._full_key(key)
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=full_key, VersionId=version_id)
            return resp["Body"].read()
        except ClientError:
            return None