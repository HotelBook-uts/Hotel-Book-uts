"""Errores de negocio del dominio.

Las capas de repositorio y servicio lanzan estos errores; la capa API
los traduce al código HTTP y al formato de respuesta que corresponda.
"""


class UsuarioNoEncontradoError(Exception):
    """El usuario solicitado no existe."""


class CorreoDuplicadoError(Exception):
    """El correo ya está registrado por otro usuario."""


class RepositorioNoDisponibleError(Exception):
    """La base de datos no está disponible o falló la consulta."""


class HabitacionNoEncontradaError(Exception):
    """La habitación solicitada no existe."""


class HabitacionNoDisponibleError(Exception):
    """La habitación ya está reservada en esas fechas o no está habilitada."""


class FechasInvalidasError(Exception):
    """Las fechas de la reserva no cumplen las reglas de negocio."""


class ReservaNoEncontradaError(Exception):
    """La reserva solicitada no existe."""


class ReservaYaCanceladaError(Exception):
    """La reserva ya estaba cancelada."""


# --------------------------------- HU-002 ---------------------------------

class CuentaNoActivaError(Exception):
    """No existe una cuenta activa con ese correo."""


class CredencialesInvalidasError(Exception):
    """La contraseña no coincide."""

    def __init__(self, intentos_restantes: int):
        super().__init__(intentos_restantes)
        self.intentos_restantes = intentos_restantes


class CuentaBloqueadaError(Exception):
    """La cuenta se bloqueó por superar el máximo de intentos fallidos."""


class TokenInvalidoError(Exception):
    """El token no es válido, expiró o la sesión fue cerrada."""


class AccesoDenegadoError(Exception):
    """El usuario no tiene permiso para esta operación."""
