import bcrypt


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña (nunca se guarda en texto plano)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña contra su hash (se usará en HU-002)."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))