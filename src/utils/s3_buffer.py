"""
Buffer video di Biznet Gio (NEO) S3 — Phase 5 decouple producer/publisher.

Producer upload MP4 ke S3 (aset berat), simpan status di `content_inventory` (DB).
Publisher ambil video ready → publish → hapus dari S3 (simpan record). Co-located VPS
(West Java) → latency rendah, no egress (decisions_production_scaling §2).

Config dari env: S3_ENDPOINT / S3_ACCESS_KEY / S3_SECRET_KEY / S3_BUCKET / S3_REGION.
Fail-loud bila config kurang (no silent default). Pisah dari R2_* (musik = Cloudflare R2).
"""

import os
from loguru import logger


class BufferError(Exception):
    """Error pada buffer S3."""
    pass


def _client():
    try:
        import boto3
        from botocore.client import Config
    except ImportError as e:
        raise BufferError("boto3 tidak terinstall.") from e
    endpoint = os.getenv("S3_ENDPOINT")
    access   = os.getenv("S3_ACCESS_KEY")
    secret   = os.getenv("S3_SECRET_KEY")
    if not (endpoint and access and secret):
        raise BufferError(
            "Config S3 buffer kurang — wajib S3_ENDPOINT + S3_ACCESS_KEY + S3_SECRET_KEY di .env."
        )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name=os.getenv("S3_REGION", "idn"),
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    b = os.getenv("S3_BUCKET")
    if not b:
        raise BufferError("S3_BUCKET tidak diset di .env (no default).")
    return b


def upload(local_path: str, s3_key: str) -> str:
    """Upload file lokal → S3 buffer. Return s3_key. Raise BufferError jika gagal."""
    try:
        _client().upload_file(local_path, _bucket(), s3_key)
        logger.info(f"[s3_buffer] upload OK: {s3_key}")
        return s3_key
    except BufferError:
        raise
    except Exception as e:
        raise BufferError(f"upload gagal ({s3_key}): {e}") from e


def download(s3_key: str, local_path: str) -> str:
    """Download dari S3 buffer → file lokal (untuk publish). Return local_path."""
    try:
        _client().download_file(_bucket(), s3_key, local_path)
        return local_path
    except Exception as e:
        raise BufferError(f"download gagal ({s3_key}): {e}") from e


def delete(s3_key: str) -> None:
    """Hapus aset dari buffer setelah published (best-effort)."""
    try:
        _client().delete_object(Bucket=_bucket(), Key=s3_key)
        logger.info(f"[s3_buffer] delete: {s3_key}")
    except Exception as e:
        logger.warning(f"[s3_buffer] delete gagal ({s3_key}, non-fatal): {e}")


def list_keys(prefix: str = "") -> list:
    """List objek buffer → [(key, size_bytes, last_modified_utc)]. Untuk janitor/rekonsiliasi."""
    out = []
    cl = _client()
    paginator = cl.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=_bucket(), Prefix=prefix):
        for o in page.get("Contents", []):
            out.append((o["Key"], o.get("Size", 0), o.get("LastModified")))
    return out
