from typing import Optional

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.domain.usuario import Usuario, UsuarioConsulta, UsuarioCreate
from app.repositories.usuario_repository import UsuarioRepository


class UsuarioService:
    def __init__(self, repo: UsuarioRepository):
        # Inyección de dependencias: recibe el repositorio, no lo crea
        self.repo = repo

    def registrar(self, data: UsuarioCreate) -> Usuario:
        # Regla de negocio: un correo solo puede registrarse una vez
        if self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario registrado con ese correo",
            )
        usuario = self.repo.create(data, hash_password(data.password))
        # Se devuelve sin el hash de la contraseña
        return Usuario(**usuario.model_dump(exclude={"password_hash"}))

    def consultar(self, usuario_id: int) -> Optional[UsuarioConsulta]:
        # Regla de negocio: validar que el usuario exista
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            return None
        # Solo se exponen los datos públicos (nunca la contraseña)
        return UsuarioConsulta(id=usuario.id, nombre=usuario.nombre, correo=usuario.email)