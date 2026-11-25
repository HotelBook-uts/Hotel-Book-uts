from typing import Optional

from app.domain.usuario import UsuarioCreate, UsuarioInDB


class UsuarioRepository:
    """Base de datos simulada en memoria."""

    def __init__(self):
        self._db: dict[int, UsuarioInDB] = {}
        self._next_id: int = 1

    def get_by_id(self, usuario_id: int) -> Optional[UsuarioInDB]:
        return self._db.get(usuario_id)

    def update_perfil(
        self, usuario_id: int, nombre: str, email: str, telefono: Optional[str]
    ) -> Optional[UsuarioInDB]:
        usuario = self._db.get(usuario_id)
        if not usuario:
            return None
        # Solo se actualizan datos de contacto; el hash de la contraseña no se toca
        actualizado = usuario.model_copy(
            update={"nombre": nombre, "email": email, "telefono": telefono})
        self._db[usuario_id] = actualizado
        return actualizado

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