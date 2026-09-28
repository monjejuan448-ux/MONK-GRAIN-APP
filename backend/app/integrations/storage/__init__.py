"""Selección del almacenamiento según la configuración."""

from functools import lru_cache

from app.integrations.storage.base import StorageProvider
from app.integrations.storage.s3 import S3Storage

__all__ = ["StorageProvider", "get_storage"]


@lru_cache
def get_storage() -> StorageProvider:
    """Devuelve el almacenamiento configurado.

    Hoy solo hay una implementación compatible con S3, que sirve tanto para
    MinIO en desarrollo como para S3 en producción: la diferencia está en las
    variables `S3_*`, no en el código.
    """
    return S3Storage()
