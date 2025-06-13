from __future__ import annotations

import asyncio
import os
import uuid
from typing import Final

from aiobotocore.session import get_session
from botocore.config import Config

from app.utils.content_type import get_content_type

R2_ACCESS_KEY_ID: Final[str | None] = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY: Final[str | None] = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL: Final[str | None] = os.getenv("R2_ENDPOINT_URL")
R2_BUCKET: Final[str | None] = os.getenv("R2_BUCKET")
R2_REGION: Final[str] = os.getenv("R2_REGION", "auto")
R2_PUBLIC_BASE: Final[str | None] = os.getenv("R2_PUBLIC_BASE")  # e.g. https://<account>.r2.cloudflarestorage.com/<bucket>

if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET]):
    raise RuntimeError("R2 credentials are incomplete: ensure env vars R2_* are set")


class R2Uploader:
    """
    Asynchronous uploader for Cloudflare R2 compatible S3 API.
    Keeps a single aiobotocore client for the lifespan of the app.
    """

    _session = get_session()

    def __init__(self) -> None:
        self._client = None

    async def __aenter__(self):
        if self._client is None:
            self._client = await self._session.create_client(
                "s3",
                region_name=R2_REGION,
                endpoint_url=R2_ENDPOINT_URL,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
            ).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    async def upload_bytes(
        self,
        data: bytes,
        *,
        key: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
        pack_name: str | None = None,
    ) -> str:
        """
        Upload raw bytes to R2 and return a public URL.
        If pack_name is provided, files will be stored in a folder with that name.
        """
        if key is None:
            if not filename:
                filename = "file.bin"
            # Если указано имя пака, создаем структуру папок packs/{pack_name}/{filename}
            if pack_name:
                # Заменяем пробелы на подчеркивания для безопасного использования в пути
                safe_pack_name = pack_name.replace(" ", "_").lower()
                key = f"packs/{safe_pack_name}/{filename}"
            else:
                key = f"packs/{uuid.uuid4()}/{filename}"
        if content_type is None and filename:
            content_type = get_content_type(filename)

        await self._client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type or "application/octet-stream",
        )

        if R2_PUBLIC_BASE:
            return f"{R2_PUBLIC_BASE}/{key}"
        # Fallback pre-signed URL (1 year expiry) if PUBLIC_BASE undefined
        presigned = await self._client.generate_presigned_url(
            "get_object", Params={"Bucket": R2_BUCKET, "Key": key}, ExpiresIn=31536000
        )
        return presigned

    async def upload_files_bulk(self, *file_tuples, pack_name: str | None = None):
        """
        Helper for parallel uploads.
        file_tuples = [ (bytes, filename) , ... ]
        Returns list[str] of URLs preserving order.
        If pack_name is provided, files will be stored in a folder with that name.
        """
        async with self:
            coros = [
                self.upload_bytes(buf, filename=name, key=None, pack_name=pack_name) for buf, name in file_tuples
            ]
            return await asyncio.gather(*coros)
