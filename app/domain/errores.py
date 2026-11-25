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
