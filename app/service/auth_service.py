from datetime import datetime, timezone

import jwt

from app.core.config import settings
from app.core.security import crear_token, decodificar_token, verify_password
from app.domain.auth import DatosSesion, LoginRequest, SesionUsuario
from app.domain.errores import (CredencialesInvalidasError, CuentaBloqueadaError,
                                CuentaNoActivaError, TokenInvalidoError)
from app.domain.usuario import EstadoCuenta, Rol
from app.repositories.intento_acceso_repository import IntentoAccesoRepository
from app.repositories.sesion_repository import SesionRepository
from app.repositories.usuario_repository import UsuarioRepository


class AuthService:
    def __init__(
        self,
        usuario_repo: UsuarioRepository,
        intento_repo: IntentoAccesoRepository,
        sesion_repo: SesionRepository,
        max_intentos: int = settings.MAX_INTENTOS_FALLIDOS,
    ):
        # Inyección de dependencias: recibe los repositorios, no los crea
        self.usuario_repo = usuario_repo
        self.intento_repo = intento_repo
        self.sesion_repo = sesion_repo
        self.max_intentos = max_intentos

    # HU-002: inicio de sesión con control de intentos fallidos
    def login(self, data: LoginRequest) -> DatosSesion:
        usuario = self.usuario_repo.get_by_email(data.correo)

        # Regla de negocio: la cuenta debe existir y no estar inactiva
        if not usuario or usuario.estado == EstadoCuenta.INACTIVA:
            self.intento_repo.registrar(data.correo, usuario.id if usuario else None,
                                        False, "Cuenta inexistente o inactiva")
            raise CuentaNoActivaError(data.correo)

        # Regla de negocio: una cuenta bloqueada no puede iniciar sesión
        if usuario.estado == EstadoCuenta.BLOQUEADA:
            self.intento_repo.registrar(data.correo, usuario.id, False, "Cuenta bloqueada")
            raise CuentaBloqueadaError(data.correo)

        # Regla de negocio: al superar el máximo de intentos fallidos se bloquea la cuenta
        if not verify_password(data.contrasena, usuario.password_hash):
            intentos = usuario.intentos_fallidos + 1
            bloquear = intentos >= self.max_intentos
            estado = EstadoCuenta.BLOQUEADA if bloquear else EstadoCuenta.ACTIVA
            self.usuario_repo.update_seguridad(usuario.id, intentos, estado)
            self.intento_repo.registrar(
                data.correo, usuario.id, False,
                "Cuenta bloqueada por intentos fallidos" if bloquear else "Contraseña incorrecta")
            if bloquear:
                raise CuentaBloqueadaError(data.correo)
            raise CredencialesInvalidasError(self.max_intentos - intentos)

        # Inicio exitoso: se reinicia el contador y se genera el token con el rol
        self.usuario_repo.update_seguridad(usuario.id, 0, EstadoCuenta.ACTIVA)
        self.intento_repo.registrar(data.correo, usuario.id, True, "Inicio de sesión exitoso")
        token, _, expira = crear_token(usuario.id, usuario.rol.value)
        return DatosSesion(
            correo=usuario.email,
            token=token,
            rol=usuario.rol,
            expiraEn=expira.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    # HU-002: cierre de sesión, el token deja de servir
    def logout(self, sesion: SesionUsuario) -> None:
        self.sesion_repo.revocar(sesion.jti, sesion.expira)

    # HU-002: valida el token de una petición y devuelve quién es el usuario
    def validar_token(self, token: str) -> SesionUsuario:
        try:
            payload = decodificar_token(token)
            usuario_id = int(payload["sub"])
            rol = Rol(payload["rol"])
        except (jwt.InvalidTokenError, ValueError, KeyError):
            raise TokenInvalidoError()

        if self.sesion_repo.esta_revocado(payload["jti"]):
            raise TokenInvalidoError()

        # Si la cuenta se bloqueó o desactivó, el token ya no sirve
        usuario = self.usuario_repo.get_by_id(usuario_id)
        if not usuario or usuario.estado != EstadoCuenta.ACTIVA:
            raise TokenInvalidoError()

        return SesionUsuario(
            usuarioId=usuario_id, rol=rol, jti=payload["jti"],
            expira=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
