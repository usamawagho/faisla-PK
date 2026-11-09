from dataclasses import dataclass
from time import time

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from cloudinary.exceptions import Error as CloudinaryError

from app.core.config import Settings, settings


class CloudinaryStorageError(Exception):
    pass


class CloudinaryStorageNotConfigured(CloudinaryStorageError):
    pass


@dataclass(frozen=True)
class StoredAsset:
    secure_url: str


class CloudinaryStorage:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def _configure(self) -> None:
        if not all(
            (
                self.config.CLOUDINARY_CLOUD_NAME,
                self.config.CLOUDINARY_API_KEY,
                self.config.CLOUDINARY_API_SECRET,
            )
        ):
            raise CloudinaryStorageNotConfigured(
                "Cloudinary credentials are not configured"
            )
        cloudinary.config(
            cloud_name=self.config.CLOUDINARY_CLOUD_NAME,
            api_key=self.config.CLOUDINARY_API_KEY,
            api_secret=self.config.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def upload(self, content: bytes, public_id: str) -> StoredAsset:
        self._configure()
        try:
            result = cloudinary.uploader.upload(
                content,
                resource_type="raw",
                type="authenticated",
                public_id=public_id,
                filename=public_id.rsplit("/", maxsplit=1)[-1],
                overwrite=False,
                unique_filename=False,
                use_filename=False,
                headers={"X-Robots-Tag": "noindex"},
                timeout=30,
            )
        except CloudinaryError as exc:
            raise CloudinaryStorageError("Cloudinary upload failed") from exc

        secure_url = result.get("secure_url")
        if not isinstance(secure_url, str) or not secure_url.startswith("https://"):
            raise CloudinaryStorageError("Cloudinary returned an invalid asset URL")
        return StoredAsset(secure_url=secure_url)

    def get_download_url(self, public_id: str, expires_in_seconds: int = 600) -> str:
        self._configure()
        return cloudinary.utils.private_download_url(
            public_id,
            None,
            resource_type="raw",
            type="authenticated",
            attachment=True,
            expires_at=int(time()) + expires_in_seconds,
        )

    def delete(self, public_id: str) -> None:
        self._configure()
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type="raw",
                type="authenticated",
                invalidate=True,
                timeout=30,
            )
        except CloudinaryError as exc:
            raise CloudinaryStorageError("Cloudinary deletion failed") from exc
        if result.get("result") not in {"ok", "not found"}:
            raise CloudinaryStorageError("Cloudinary did not confirm asset deletion")
