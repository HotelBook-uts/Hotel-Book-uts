from enum import Enum
from typing import Optional

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    telefono: Optional[str] = Field(default=None, pattern=r"^\+?\d{7,15}$")

    # Regla de negocio: limpiar espacios y dar formato al nombre
    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, v: str) -> str:
        return v.strip().title()

    # Regla de negocio: el correo se guarda en minúsculas para evitar duplicados
    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return v.lower()


# Lo que envía el cliente para REGISTRARSE (contraseña en texto plano)
class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=72)

    # Regla de negocio: al menos una letra y un número
    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError(
                "La contraseña debe contener al menos una letra y un número")
        # bcrypt solo admite hasta 72 bytes
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga")
        return v


# Lo que devuelve la API (nunca incluye la contraseña)
class Usuario(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# HU-001: formato de respuesta del registro: {mensaje, data, success}
class RespuestaRegistro(BaseModel):
    mensaje: str
    data: Optional[Usuario] = None
    success: bool


# HU-002: roles del sistema
class Rol(str, Enum):
    CLIENTE = "CLIENTE"
    HOTELERO = "HOTELERO"
    ADMINISTRADOR = "ADMINISTRADOR"


# HU-002: estado de la cuenta
class EstadoCuenta(str, Enum):
    ACTIVA = "ACTIVA"
    BLOQUEADA = "BLOQUEADA"
    INACTIVA = "INACTIVA"


# Lo que se guarda internamente: incluye el hash de la contraseña
class UsuarioInDB(Usuario):
    password_hash: str
    # HU-002: todo usuario nuevo es CLIENTE con cuenta ACTIVA
    rol: Rol = Rol.CLIENTE
    estado: EstadoCuenta = EstadoCuenta.ACTIVA
    intentos_fallidos: int = 0


MENSAJE_CORREO_INVALIDO = "Formato de correo no válido. Debe ser usuario@dominio.com"


def validar_formato_correo(v: str) -> str:
    """Regla de negocio: el correo debe tener formato usuario@dominio.com.
    Se devuelve limpio y en minúsculas."""
    try:
        validate_email(v, check_deliverability=False)
    except EmailNotValidError:
        raise ValueError(MENSAJE_CORREO_INVALIDO)
    return v.strip().lower()


# ---------------------------------------------------------------------------
# HU-004: consulta y actualización del perfil del cliente
# ---------------------------------------------------------------------------


# Perfil del cliente sin datos sensibles (nunca incluye la contraseña)
class PerfilUsuario(BaseModel):
    usuarioId: int
    nombres: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None


# Lo que envía el cliente para ACTUALIZAR su perfil
class PerfilUpdate(BaseModel):
    nombres: str = Field(..., min_length=2, max_length=100,
                         description="Nombres y apellidos del cliente")
    correo: str = Field(..., description="Correo electrónico (usuario@dominio.com)")
    telefono: Optional[str] = Field(default=None, pattern=r"^\+?\d{7,15}$",
                                    description="Teléfono de contacto")

    # Regla de negocio: limpiar espacios y dar formato a los nombres
    @field_validator("nombres")
    @classmethod
    def limpiar_nombres(cls, v: str) -> str:
        return v.strip().title()

    # Regla de negocio: el correo debe tener formato válido y se guarda en minúsculas
    @field_validator("correo")
    @classmethod
    def validar_correo(cls, v: str) -> str:
        return validar_formato_correo(v)


# Formato estándar de respuesta del perfil: {mensaje, data, success}
class RespuestaPerfil(BaseModel):
    mensaje: str
    data: Optional[PerfilUsuario] = None
    success: bool
