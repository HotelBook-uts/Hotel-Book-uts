"""Instancias compartidas entre routers y dependencia de sesión (HU-002)."""

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.validacion import ErrorAPI
from app.domain.auth import SesionUsuario
from app.domain.errores import TokenInvalidoError
from app.repositories.intento_acceso_repository import IntentoAccesoRepository
from app.repositories.sesion_repository import SesionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.service.auth_service import AuthService

# Un solo repositorio de cada tipo, así los datos se comparten entre peticiones
usuario_repo = UsuarioRepository()
intento_repo = IntentoAccesoRepository()
sesion_repo = SesionRepository()
auth_service = AuthService(usuario_repo, intento_repo, sesion_repo)

MSG_SESION_INVALIDA = "Sesión no válida o expirada. Inicie sesión nuevamente"

# Agrega el botón "Authorize" en Swagger para enviar el token
_bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en /api/v1/auth/login")


def get_sesion(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> SesionUsuario:
    """Valida el header 'Authorization: Bearer <token>' y devuelve el usuario en sesión."""
    if credenciales is None:
        raise ErrorAPI(status.HTTP_401_UNAUTHORIZED,
                       "Debe iniciar sesión para realizar esta operación")
    try:
        return auth_service.validar_token(credenciales.credentials)
    except TokenInvalidoError:
        raise ErrorAPI(status.HTTP_401_UNAUTHORIZED, MSG_SESION_INVALIDA)
