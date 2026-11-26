"""Respuestas de error con el formato {mensaje, data, success} para la capa API."""

from typing import Any, Callable, Optional, Type

from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.domain.usuario import MENSAJE_CORREO_INVALIDO


class ErrorAPI(Exception):
    """Error que se responde directamente con {mensaje, data, success: false}.

    Se usa en las dependencias (por ejemplo, la validación del token), donde
    no se puede devolver un JSONResponse.
    """

    def __init__(self, codigo: int, mensaje: str, data: Any = None):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.data = data


def respuesta_error(codigo: int, mensaje: str, data: Any = None) -> JSONResponse:
    return JSONResponse(status_code=codigo,
                        content={"mensaje": mensaje, "data": data, "success": False})


async def manejar_error_api(_: Request, exc: ErrorAPI) -> JSONResponse:
    return respuesta_error(exc.codigo, exc.mensaje, exc.data)


_MENSAJES = {
    "missing": "es obligatorio",
    "string_type": "debe ser texto",
    "string_too_short": "debe tener al menos {min_length} caracteres",
    "string_too_long": "debe tener máximo {max_length} caracteres",
    "string_pattern_mismatch": "no tiene un formato válido",
    "int_parsing": "debe ser un número entero",
    "int_type": "debe ser un número entero",
    "float_parsing": "debe ser un número",
    "greater_than": "debe ser mayor que {gt}",
    "greater_than_equal": "debe ser mayor o igual que {ge}",
    "less_than_equal": "debe ser menor o igual que {le}",
    "date_from_datetime_parsing": "debe ser una fecha válida (AAAA-MM-DD)",
    "json_invalid": "el cuerpo no es un JSON válido",
}


def _traducir(error: dict) -> str:
    """Mensaje de validación en español; si no está traducido, se deja el original."""
    plantilla = _MENSAJES.get(error.get("type", ""))
    if not plantilla:
        return str(error.get("msg"))
    try:
        return plantilla.format(**error.get("ctx", {}))
    except (KeyError, IndexError):
        return str(error.get("msg"))


def ruta_validacion_400(
    mensaje_base: str, data_error: Optional[Callable[[Request], Any]] = None
) -> Type[APIRoute]:
    """Crea una clase de ruta que responde 400 con {mensaje, data, success}
    cuando el cuerpo no es válido, en vez del 422 por defecto de FastAPI.

    Se aplica solo a los endpoints que la historia de usuario lo pide.
    """

    class RutaValidacion400(APIRoute):
        def get_route_handler(self) -> Callable:
            handler_original = super().get_route_handler()

            async def handler(request: Request) -> Response:
                try:
                    return await handler_original(request)
                except RequestValidationError as exc:
                    detalles = []
                    for error in exc.errors():
                        loc = error.get("loc", ())
                        es_correo = "correo" in loc or "email" in loc
                        if es_correo and error.get("type") != "missing":
                            detalles.append(MENSAJE_CORREO_INVALIDO)
                        elif error.get("type") == "value_error":
                            # Reglas de negocio propias: se muestra solo el mensaje
                            detalles.append(str(error.get("ctx", {}).get("error", error.get("msg"))))
                        else:
                            campo = ".".join(str(p) for p in loc[1:]) or "cuerpo"
                            detalles.append(f"{campo}: {_traducir(error)}")
                    # Sin mensajes repetidos (ej. correo inválido detectado dos veces),
                    # separados por punto: "Base. Detalle 1. Detalle 2"
                    detalles = list(dict.fromkeys(d.rstrip(".") for d in detalles))
                    data = await data_error(request) if data_error else None
                    return respuesta_error(status.HTTP_400_BAD_REQUEST,
                                           f"{mensaje_base} {'. '.join(detalles)}", data)

            return handler

    return RutaValidacion400
