import logging
import os
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.client import Config
except ImportError:
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]

logger = logging.getLogger("msut.storage")

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "msut")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if boto3 is None or Config is None:
        raise RuntimeError("boto3 未安装")
    if not R2_ACCOUNT_ID or not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        raise RuntimeError("R2 配置不完整，请检查环境变量")
    endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    _client = boto3.client(  # type: ignore[union-attr]
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),  # type: ignore[union-attr]
        region_name="auto",
    )
    logger.info("R2 client ready: bucket=%s", R2_BUCKET)
    return _client


def build_public_url(key: str) -> str:
    if R2_PUBLIC_URL:
        return f"{R2_PUBLIC_URL}/{key}"
    return f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{R2_BUCKET}/{key}"


def upload_bytes(key: str, data: bytes, content_type: str = "") -> str:
    client = _get_client()
    extra = {"ContentType": content_type} if content_type else {}
    client.put_object(Bucket=R2_BUCKET, Key=key, Body=data, **extra)
    url = build_public_url(key)
    logger.info("R2 upload_bytes: key=%s url=%s size=%s", key, url, len(data))
    return url


def upload_file(key: str, file_path: Path, content_type: str = "") -> str:
    client = _get_client()
    extra = {"ContentType": content_type} if content_type else {}
    client.upload_file(str(file_path), R2_BUCKET, key, ExtraArgs=extra)
    url = build_public_url(key)
    logger.info("R2 upload_file: key=%s url=%s path=%s", key, url, file_path)
    return url


def get_presigned_url(key: str, expires: int = 3600) -> str:
    client = _get_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
    return url


def get_presigned_download_url(
    key: str, filename: str, expires: int = 3600
) -> str:
    client = _get_client()
    from urllib.parse import quote

    safe_ascii = filename.encode("ascii", "ignore").decode("ascii") or "file"
    safe_ascii = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe_ascii)
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": R2_BUCKET,
            "Key": key,
            "ResponseContentDisposition": (
                f'attachment; filename="{safe_ascii}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
        },
        ExpiresIn=expires,
    )
    return url


def delete_object(key: str):
    client = _get_client()
    client.delete_object(Bucket=R2_BUCKET, Key=key)
    logger.info("R2 delete: key=%s", key)
