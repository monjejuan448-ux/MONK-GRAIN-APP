"""Contrato común del almacenamiento de archivos.

Los módulos de dominio dependen de esta interfaz y nunca de S3 ni de MinIO, del
mismo modo que el checkout depende de `PaymentProvider` y no de una pasarela
concreta (ADR-03). Cambiar de proveedor —o pasar de MinIO en desarrollo a S3 en
producción— es escribir una clase que la implemente.
"""

from abc import ABC, abstractmethod

# Prefijos que el navegador puede leer sin credenciales: son el escaparate.
# Todo lo que no empiece por uno de ellos —los certificados, en particular— solo
# se alcanza con una URL firmada de vida corta.
PUBLIC_PREFIXES = ("products/", "producers/", "demo/")

CERTIFICATE_PREFIX = "certifications/"


def is_public(key: str) -> bool:
    return key.startswith(PUBLIC_PREFIXES)


class StorageProvider(ABC):
    """Guarda y elimina archivos, y sabe con qué URL se sirven."""

    @abstractmethod
    def put(self, key: str, content: bytes, content_type: str) -> str:
        """Guarda el contenido bajo `key` y devuelve esa misma clave."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Elimina el archivo. No falla si ya no existe."""

    @abstractmethod
    def public_url(self, key: str) -> str:
        """URL con la que el navegador descarga un archivo público."""

    @abstractmethod
    def signed_url(self, key: str, expires_in: int = 300) -> str:
        """Enlace temporal para un archivo privado.

        Se usa con los certificados: quien tiene derecho a verlos recibe un
        enlace que caduca en minutos, en vez de una URL permanente que seguiría
        funcionando si alguien la reenvía.
        """
