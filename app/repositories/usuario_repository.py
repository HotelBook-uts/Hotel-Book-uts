from typing import Optional

from app.domain.usuario import UsuarioCreate, UsuarioInDB


class UsuarioRepository:
    """Base de datos simulada en memoria."""

    def __init__(self):
        self._db: dict[int, UsuarioInDB] = {}
        self._next_id: int = 1

    def get_by_email(self, email: str) -> Optional[UsuarioInDB]:
        return next(
            (u for u in self._db.values() if u.email.lower() == email.lower()),
            None,
        )

    def create(self, data: UsuarioCreate, password_hash: str) -> UsuarioInDB:
        usuario = UsuarioInDB(
            id=self._next_id,
            password_hash=password_hash,
            **data.model_dump(exclude={"password"}),
        )
        self._db[self._next_id] = usuario
        self._next_id += 1
        return usuario