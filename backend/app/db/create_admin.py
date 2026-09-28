"""Creación de una cuenta administradora.

El primer administrador no puede crearse desde la interfaz —haría falta ya ser
administrador para hacerlo—, así que se genera con este script desde el
servidor, que es donde se puede acreditar el acceso legítimo.

Uso:
    docker compose exec backend python -m app.db.create_admin
    docker compose exec backend python -m app.db.create_admin --email otro@dominio.co
"""

import argparse
import secrets
import string
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password, validate_password_strength
from app.db.session import SessionLocal
from app.models.enums import RoleCode, UserStatus
from app.models.user import Role, User, UserRole

logger = get_logger(__name__)

DEFAULT_EMAIL = "admin@monkgrain.co"


def generate_password(length: int = 20) -> str:
    """Genera una contraseña aleatoria robusta.

    Se usa `secrets`, no `random`: este último es predecible y no sirve para
    material criptográfico.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if not validate_password_strength(candidate):
            return candidate


def create_admin(email: str, password: str | None, full_name: str) -> None:
    configure_logging()
    session = SessionLocal()

    try:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"Ya existe una cuenta con el correo {email}.")  # noqa: T201
            if RoleCode.ADMIN.value in existing.role_codes:
                print("Esa cuenta ya tiene el rol de administrador.")  # noqa: T201
                return

            role = session.scalar(select(Role).where(Role.code == RoleCode.ADMIN.value))
            if role is None:
                print(  # noqa: T201
                    "Falta el rol 'admin'. Ejecuta primero: python -m app.db.seed"
                )
                sys.exit(1)

            session.add(UserRole(user_id=existing.id, role_id=role.id))
            session.commit()
            print(f"Se concedió el rol de administrador a {email}.")  # noqa: T201
            return

        role = session.scalar(select(Role).where(Role.code == RoleCode.ADMIN.value))
        if role is None:
            print(  # noqa: T201
                "Falta el rol 'admin' en la base de datos.\n"
                "Ejecuta primero: docker compose exec backend python -m app.db.seed"
            )
            sys.exit(1)

        generated = password is None
        final_password = password or generate_password()

        problems = validate_password_strength(final_password)
        if problems:
            print("La contraseña no cumple los requisitos:")  # noqa: T201
            for problem in problems:
                print(f"  - {problem}")  # noqa: T201
            sys.exit(1)

        user = User(
            email=email,
            password_hash=hash_password(final_password),
            full_name=full_name,
            # La cuenta queda activa: el administrador se crea desde el
            # servidor, donde el acceso ya está acreditado, y exigirle
            # verificación por correo bloquearía la puesta en marcha.
            status=UserStatus.ACTIVE,
            data_consent=True,
            data_consent_at=datetime.now(UTC),
        )
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()

        logger.info("admin_created", email=email)

        print("\nAdministrador creado.")  # noqa: T201
        print(f"  correo     : {email}")  # noqa: T201
        if generated:
            print(f"  contraseña : {final_password}")  # noqa: T201
            print(  # noqa: T201
                "\nGuárdala ahora: no vuelve a mostrarse y no puede recuperarse "
                "de la base de datos, donde solo queda su hash."
            )
        else:
            print("  contraseña : la que indicaste")  # noqa: T201

    except Exception:
        session.rollback()
        logger.exception("admin_creation_failed")
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea una cuenta administradora.")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Correo de la cuenta")
    parser.add_argument(
        "--password",
        default=None,
        help="Contraseña. Si se omite, se genera una aleatoria y se muestra una sola vez.",
    )
    parser.add_argument("--name", default="Administrador MONK GRAIN", help="Nombre completo")
    args = parser.parse_args()

    create_admin(args.email, args.password, args.name)


if __name__ == "__main__":
    main()
