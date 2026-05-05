import hashlib
from pathlib import Path

import boto3
from botocore.client import Config

from apps.api.core.config import settings


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.storage_region,
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key_id,
        aws_secret_access_key=settings.storage_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


def upload_file_to_storage(local_path: Path, object_key: str, content_type: str = "application/octet-stream") -> dict:
    if settings.storage_provider.lower() == "local":
        return {
            "provider": "local",
            "bucket": "local",
            "storage_key": str(local_path),
            "signed_url": f"file://{local_path}",
        }

    client = _s3_client()
    client.upload_file(
        Filename=str(local_path),
        Bucket=settings.storage_bucket,
        Key=object_key,
        ExtraArgs={"ContentType": content_type},
    )
    signed_url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": object_key},
        ExpiresIn=settings.storage_signed_url_expiry_seconds,
    )
    return {
        "provider": settings.storage_provider,
        "bucket": settings.storage_bucket,
        "storage_key": object_key,
        "signed_url": signed_url,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
