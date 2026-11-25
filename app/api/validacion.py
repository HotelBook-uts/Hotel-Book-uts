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
                        if "correo" in loc:
                            detalles.append(MENSAJE_CORREO_INVALIDO)
                        else:
                            campo = ".".join(str(p) for p in loc[1:])
                            detalles.append(f"{campo}: {error.get('msg')}")
                    data = await data_error(request) if data_error else None
                    return respuesta_error(status.HTTP_400_BAD_REQUEST,
                                           " ".join([mensaje_base, *detalles]), data)

            return handler

    return RutaValidacion400
