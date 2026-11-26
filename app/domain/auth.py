"""HU-002: modelos del inicio y cierre de sesión."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.usuario import Rol, validar_formato_correo


# Lo que envía el usuario para INICIAR SESIÓN
class LoginRequest(BaseModel):
    correo: str = Field(..., description="Correo de la cuenta (usuario@dominio.com)")
    contrasena: str = Field(..., min_length=1, max_length=72, description="Contraseña")

    model_config = ConfigDict(json_schema_extra={
        "example": {"correo": "laura.gomez@correo.com", "contrasena": "clave1234"}
    })

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, v: str) -> str:
        return validar_formato_correo(v)


# Datos de la sesión que se devuelven al iniciar sesión
class DatosSesion(BaseModel):
    correo: str
    token: Optional[str] = None
    rol: Optional[Rol] = None
    expiraEn: Optional[str] = None


# Formato de respuesta del login: {mensaje, data, success}
class RespuestaLogin(BaseModel):
    mensaje: str
    data: Optional[DatosSesion] = None
    success: bool


# Formato de respuesta simple: {mensaje, success}
class RespuestaAuth(BaseModel):
    mensaje: str
    success: bool


# Usuario autenticado a partir de un token válido
class SesionUsuario(BaseModel):
    usuarioId: int
    rol: Rol
    jti: str
    expira: datetime

    @property
    def es_admin(self) -> bool:
        return self.rol == Rol.ADMINISTRADOR

    # Regla de negocio: un usuario solo accede a lo suyo, salvo el administrador
    def puede_acceder_a(self, usuario_id: int) -> bool:
        return self.es_admin or self.usuarioId == usuario_id


# Registro de cada intento de inicio de sesión (tabla intentos_acceso)
class IntentoAcceso(BaseModel):
    id: int
    correo: str
    usuarioId: Optional[int] = None
    exitoso: bool
    motivo: str
    fecha: datetime
