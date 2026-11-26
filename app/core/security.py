from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import settings

ALGORITMO_JWT = "HS256"


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña (nunca se guarda en texto plano)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """HU-002: comprueba una contraseña contra su hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def crear_token(usuario_id: int, rol: str, minutos: Optional[int] = None) -> tuple[str, str, datetime]:
    """HU-002: genera un JWT firmado con el id y el rol del usuario.

    Devuelve (token, jti, expiracion). El jti identifica la sesión para poder
    invalidarla al cerrar sesión.
    """
    ahora = datetime.now(timezone.utc).replace(microsecond=0)
    expira = ahora + timedelta(minutes=minutos or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = uuid4().hex
    payload = {"sub": str(usuario_id), "rol": rol, "jti": jti, "iat": ahora, "exp": expira}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITMO_JWT)
    return token, jti, expira


def decodificar_token(token: str) -> dict:
    """HU-002: valida la firma y la expiración del JWT.

    Lanza jwt.InvalidTokenError (o ExpiredSignatureError) si no es válido.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITMO_JWT],
                      options={"require": ["sub", "rol", "jti", "exp"]})
