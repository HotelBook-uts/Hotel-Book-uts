from fastapi import HTTPException, status

from app.core.security import hash_password
from app.domain.errores import CorreoDuplicadoError, UsuarioNoEncontradoError
from app.domain.usuario import (PerfilUpdate, PerfilUsuario, Usuario,
                                UsuarioCreate, UsuarioInDB)
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

    # HU-004: consulta del perfil del cliente
    # TODO HU-002: validar que quien consulta sea el dueño del perfil o un administrador
    def consultar_perfil(self, usuario_id: int) -> PerfilUsuario:
        usuario = self.repo.get_by_id(usuario_id)
        if not usuario:
            raise UsuarioNoEncontradoError(usuario_id)
        return self._a_perfil(usuario)

    # HU-004: actualización del perfil del cliente
    # TODO HU-002: validar que quien actualiza sea el dueño del perfil o un administrador
    def actualizar_perfil(self, usuario_id: int, data: PerfilUpdate) -> PerfilUsuario:
        if not self.repo.get_by_id(usuario_id):
            raise UsuarioNoEncontradoError(usuario_id)

        # Regla de negocio: el correo sigue siendo único
        otro = self.repo.get_by_email(data.correo)
        if otro and otro.id != usuario_id:
            raise CorreoDuplicadoError(data.correo)

        usuario = self.repo.update_perfil(
            usuario_id, data.nombres, data.correo, data.telefono)
        return self._a_perfil(usuario)

    @staticmethod
    def _a_perfil(usuario: UsuarioInDB) -> PerfilUsuario:
        # Solo se exponen los datos de contacto (nunca la contraseña)
        return PerfilUsuario(
            usuarioId=usuario.id,
            nombres=usuario.nombre,
            correo=usuario.email,
            telefono=usuario.telefono,
        )