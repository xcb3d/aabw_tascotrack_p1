from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...
    async def get(self, uri: str) -> bytes: ...
    async def delete(self, uri: str) -> None: ...


class LocalObjectStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key.replace("\\", "/")).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("object key escapes storage root")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        del content_type
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        normalized_key = key.replace("\\", "/")
        return f"local://{normalized_key}"

    async def get(self, uri: str) -> bytes:
        if not uri.startswith("local://"):
            raise ValueError("unsupported local object URI")
        return await asyncio.to_thread(self._path(uri[8:]).read_bytes)

    async def delete(self, uri: str) -> None:
        if not uri.startswith("local://"):
            raise ValueError("unsupported local object URI")
        path = self._path(uri[8:])
        if path.exists():
            await asyncio.to_thread(path.unlink)


class S3ObjectStore:
    def __init__(self, bucket: str, *, endpoint_url: str = "", region: str = "") -> None:
        if not bucket:
            raise ValueError("S3 bucket is required")
        import boto3
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url or None, region_name=region or None)

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(self.client.put_object, Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256")
        return f"s3://{self.bucket}/{key}"

    async def get(self, uri: str) -> bytes:
        prefix = f"s3://{self.bucket}/"
        if not uri.startswith(prefix):
            raise ValueError("object URI is outside configured bucket")
        response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=uri[len(prefix):])
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, uri: str) -> None:
        prefix = f"s3://{self.bucket}/"
        if not uri.startswith(prefix):
            raise ValueError("object URI is outside configured bucket")
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=uri[len(prefix):])


def get_object_store(settings) -> ObjectStore:
    if settings.OBJECT_STORAGE_BACKEND == "s3":
        return S3ObjectStore(settings.OBJECT_STORAGE_BUCKET, endpoint_url=settings.OBJECT_STORAGE_ENDPOINT, region=settings.OBJECT_STORAGE_REGION)
    if settings.OBJECT_STORAGE_BACKEND == "local":
        return LocalObjectStore(settings.OBJECT_STORAGE_LOCAL_ROOT)
    raise ValueError("unsupported object storage backend")
