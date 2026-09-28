"""Almacenamiento compatible con S3 (MinIO en desarrollo, S3 en producción)."""

from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.storage.base import PUBLIC_PREFIXES, StorageProvider

logger = get_logger(__name__)


class S3Storage(StorageProvider):
    def __init__(self) -> None:
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self._bucket = settings.s3_bucket

    def put(self, key: str, content: bytes, content_type: str) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                # Obliga al navegador a respetar el tipo declarado por el
                # servidor en vez de deducirlo del contenido.
                ContentDisposition="inline" if content_type.startswith("image/") else "attachment",
            )
        except ClientError as exc:
            # El detalle del proveedor va al registro, no a la respuesta.
            logger.error("storage_put_failed", key=key, error=str(exc))
            raise ExternalServiceError(
                "No pudimos guardar el archivo. Inténtalo de nuevo en unos minutos."
            ) from exc

        logger.info("storage_object_stored", key=key, bytes=len(content))
        return key

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            # Un borrado fallido no debe tumbar la operación de negocio: el
            # archivo queda huérfano y se limpia aparte.
            logger.warning("storage_delete_failed", key=key, error=str(exc))

    def public_url(self, key: str) -> str:
        return f"{settings.s3_public_url}/{self._bucket}/{key}"

    def signed_url(self, key: str, expires_in: int = 300) -> str:
        try:
            url: str = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            logger.error("storage_sign_failed", key=key, error=str(exc))
            raise ExternalServiceError("No pudimos generar el enlace al documento.") from exc

        # La firma se calcula contra el punto de acceso interno, que el
        # navegador no alcanza; se sustituye por el público conservando la
        # firma, que va en la cadena de consulta.
        return url.replace(settings.s3_endpoint_url, settings.s3_public_url, 1)

    def ensure_bucket(self) -> None:
        """Crea el bucket y deja pública **solo** la parte que es escaparate.

        Abrir el bucket entero sería cómodo y equivocado: los certificados
        llevan números de registro y datos del productor, y quedarían al alcance
        de cualquiera que probara una URL.
        """
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
            logger.info("bucket_created", bucket=self._bucket)

        self._client.put_bucket_policy(
            Bucket=self._bucket,
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [
                                f"arn:aws:s3:::{self._bucket}/{prefix}*"
                                for prefix in PUBLIC_PREFIXES
                            ],
                        }
                    ],
                }
            ),
        )
        logger.info("bucket_policy_applied", bucket=self._bucket, public=PUBLIC_PREFIXES)
