"""S3-compatible object storage adapter.

Wraps boto3 synchronous operations in ``asyncio.to_thread`` to produce
a non-blocking async interface compatible with the FastAPI event loop.
Works with MinIO (local dev), AWS S3, and GCS (via the S3-compatibility API).

Object path convention:
    ``{tenant_id}/{repository_id}/{optional/sub/path}``

All platform components that write to object storage (the ingestion
pipeline, the repository upload endpoint) must use ``storage_path()``
to build keys so that the path convention is enforced uniformly.
"""

from __future__ import annotations

import asyncio
from typing import BinaryIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings


class ObjectStorageError(Exception):
    """Raised when an object storage operation fails.

    Args:
        message:   Human-readable description of the failure.
        operation: The storage operation that failed (e.g., ``'upload'``).
        key:       The object key involved, if applicable.
    """

    def __init__(self, message: str, operation: str = '', key: str = '') -> None:
        super().__init__(message)
        self.operation = operation
        self.key = key


class ObjectStorageAdapter:
    """Async adapter for S3-compatible object storage.

    All public methods are ``async`` and safe to ``await`` from coroutines.
    boto3 network I/O is dispatched to the default thread pool executor via
    ``asyncio.to_thread`` so the event loop is never blocked.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = 'us-east-1',
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    @staticmethod
    def storage_path(tenant_id: str, repository_id: str, *parts: str) -> str:
        """Build a namespaced object storage key.

        Convention: ``{tenant_id}/{repository_id}`` or
                    ``{tenant_id}/{repository_id}/{part1}/{part2}``

        Args:
            tenant_id:     Tenant UUID string.
            repository_id: Repository UUID string.
            *parts:        Optional sub-path segments.

        Returns:
            A forward-slash-delimited S3 object key.

        Examples::

            storage_path("t1", "r1")                   → "t1/r1"
            storage_path("t1", "r1", "archive.zip")    → "t1/r1/archive.zip"
            storage_path("t1", "r1", "raw", "src.zip") → "t1/r1/raw/src.zip"
        """
        base = f'{tenant_id}/{repository_id}'
        return f"{base}/{'/'.join(parts)}" if parts else base

    async def upload_file(
        self,
        key: str,
        body: bytes | BinaryIO,
        content_type: str = 'application/octet-stream',
    ) -> None:
        """Upload an object to the bucket.

        Args:
            key:          The object key (path within the bucket).
            body:         Raw bytes or a file-like object.
            content_type: MIME type stored as object metadata.

        Raises:
            ObjectStorageError: If the upload fails.
        """
        def _upload() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
            )

        try:
            await asyncio.to_thread(_upload)
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError(
                f"Upload failed: {exc}", operation='upload', key=key
            ) from exc

    async def download_file(self, key: str) -> bytes:
        """Download an object and return its raw content.

        Args:
            key: The object key.

        Returns:
            The object content as ``bytes``.

        Raises:
            ObjectStorageError: If the download fails or the key does not exist.
        """
        def _download() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response['Body'].read()  # type: ignore[no-any-return]

        try:
            return await asyncio.to_thread(_download)
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError(
                f"Download failed: {exc}", operation='download', key=key
            ) from exc

    async def delete_object(self, key: str) -> None:
        """Delete a single object from the bucket.

        Args:
            key: The object key to delete.

        Raises:
            ObjectStorageError: If the delete call fails.
        """
        def _delete() -> None:
            self._client.delete_object(Bucket=self._bucket, Key=key)

        try:
            await asyncio.to_thread(_delete)
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError(
                f"Delete failed: {exc}", operation='delete', key=key
            ) from exc

    async def object_exists(self, key: str) -> bool:
        """Check whether an object exists without downloading it.

        Uses ``HeadObject`` which returns only metadata.

        Args:
            key: The object key.

        Returns:
            ``True`` if the object exists, ``False`` if it does not.

        Raises:
            ObjectStorageError: On unexpected errors (not a simple 404).
        """
        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError as exc:
                if exc.response['Error']['Code'] in ('404', 'NoSuchKey'):
                    return False
                raise

        try:
            return await asyncio.to_thread(_head)
        except (BotoCoreError, ClientError) as exc:
            raise ObjectStorageError(
                f"Existence check failed: {exc}", operation='head', key=key
            ) from exc

    async def ping(self) -> bool:
        """Verify storage connectivity via ``HeadBucket``.

        Returns:
            ``True`` if the bucket is reachable, ``False`` otherwise.
        """
        def _head_bucket() -> bool:
            try:
                self._client.head_bucket(Bucket=self._bucket)
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_head_bucket)


# ---------------------------------------------------------------------------
# Module-level singleton — initialized from app lifespan
# ---------------------------------------------------------------------------

class _StorageState:
    adapter: ObjectStorageAdapter | None = None


_state = _StorageState()


def initialize_storage() -> None:
    """Create the object storage adapter.

    Must be called from the application lifespan startup handler.
    """
    settings = get_settings()
    _state.adapter = ObjectStorageAdapter(
        endpoint_url=settings.object_storage_endpoint_url,
        access_key=settings.object_storage_access_key,
        secret_key=settings.object_storage_secret_key,
        bucket=settings.object_storage_bucket,
        region=settings.object_storage_region,
    )


def get_storage() -> ObjectStorageAdapter:
    """Return the active object storage adapter.

    Raises:
        RuntimeError: If ``initialize_storage()`` has not been called.
    """
    if _state.adapter is None:
        raise RuntimeError(
            'Object storage not initialized. Call initialize_storage() from the app lifespan.'
        )
    return _state.adapter
