from typing import Callable

from fastapi import APIRouter, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.domain.errores import (CorreoDuplicadoError, RepositorioNoDisponibleError,
                                UsuarioNoEncontradoError)
from app.domain.usuario import (MENSAJE_CORREO_INVALIDO, PerfilUpdate, PerfilUsuario,
                                RespuestaPerfil, Usuario, UsuarioCreate)
from app.repositories.usuario_repository import UsuarioRepository
from app.service.usuario_service import UsuarioService

# Instancias: un solo repositorio, así los datos se comparten entre peticiones
repo = UsuarioRepository()
service = UsuarioService(repo)

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def registrar_usuario(data: UsuarioCreate):
    """HU-001: registra un usuario nuevo."""
    return service.registrar(data)


# ---------------------------------------------------------------------------
# HU-004: consulta y actualización del perfil del cliente
# ---------------------------------------------------------------------------

MSG_NO_EXISTE = "No existe un cliente con el identificador indicado"
MSG_NO_ACTUALIZADO = "No fue posible actualizar el perfil."


def _respuesta(codigo: int, mensaje: str, data: PerfilUsuario | None = None) -> JSONResponse:
    cuerpo = RespuestaPerfil(mensaje=mensaje, data=data, success=False)
    return JSONResponse(status_code=codigo, content=cuerpo.model_dump())


def _perfil_vacio(usuario_id: int) -> PerfilUsuario:
    return PerfilUsuario(usuarioId=usuario_id)


def _ejemplo(mensaje: str, data: dict | None, success: bool, descripcion: str) -> dict:
    return {
        "model": RespuestaPerfil,
        "description": descripcion,
        "content": {"application/json": {"example": {"mensaje": mensaje, "data": data, "success": success}}},
    }


_EJEMPLO_PERFIL = {"usuarioId": 1024, "nombres": "Laura Gómez",
                   "correo": "laura.gomez@correo.com", "telefono": "3109876543"}
_EJEMPLO_VACIO = {"usuarioId": 99999, "nombres": None, "correo": None, "telefono": None}


class PerfilValidacionRoute(APIRoute):
    """Responde 400 con el formato {mensaje, data, success} cuando el cuerpo
    del PUT de perfil no es válido (en vez del 422 por defecto de FastAPI)."""

    def get_route_handler(self) -> Callable:
        handler_original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await handler_original(request)
            except RequestValidationError as exc:
                detalles = []
                for error in exc.errors():
                    if "correo" in error.get("loc", ()):
                        detalles.append(MENSAJE_CORREO_INVALIDO)
                    else:
                        campo = ".".join(str(p) for p in error.get("loc", ())[1:])
                        detalles.append(f"{campo}: {error.get('msg')}")
                mensaje = " ".join([MSG_NO_ACTUALIZADO, *detalles])
                return _respuesta(status.HTTP_400_BAD_REQUEST, mensaje)

        return handler


@router.get(
    "/{usuario_id}",
    response_model=RespuestaPerfil,
    summary="Consultar el perfil del cliente",
    responses={
        status.HTTP_200_OK: _ejemplo("Perfil consultado correctamente", _EJEMPLO_PERFIL, True,
                                     "Perfil encontrado"),
        status.HTTP_404_NOT_FOUND: _ejemplo(MSG_NO_EXISTE, _EJEMPLO_VACIO, False,
                                            "No existe el cliente"),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo(
            "No fue posible consultar el perfil del cliente", None, False,
            "Base de datos no disponible"),
    },
)
def consultar_perfil(usuario_id: int):
    """HU-004: consulta el perfil del cliente (nombres, correo y teléfono) por su ID,
    sin exponer datos sensibles.

    Pendiente HU-002: solo el dueño del perfil o un administrador podrán consultarlo.
    """
    try:
        perfil = service.consultar_perfil(usuario_id)
    except UsuarioNoEncontradoError:
        return _respuesta(status.HTTP_404_NOT_FOUND, MSG_NO_EXISTE, _perfil_vacio(usuario_id))
    except RepositorioNoDisponibleError:
        return _respuesta(status.HTTP_503_SERVICE_UNAVAILABLE,
                          "No fue posible consultar el perfil del cliente")
    return RespuestaPerfil(mensaje="Perfil consultado correctamente", data=perfil, success=True)


def actualizar_perfil(usuario_id: int, data: PerfilUpdate):
    """HU-004: actualiza los datos de contacto del cliente (nombres, correo y teléfono).
    El correo debe tener formato válido y no puede pertenecer a otro usuario.

    Pendiente HU-002: solo el dueño del perfil o un administrador podrán actualizarlo.
    """
    try:
        perfil = service.actualizar_perfil(usuario_id, data)
    except UsuarioNoEncontradoError:
        return _respuesta(status.HTTP_404_NOT_FOUND, MSG_NO_EXISTE, _perfil_vacio(usuario_id))
    except CorreoDuplicadoError:
        return _respuesta(status.HTTP_409_CONFLICT,
                          f"{MSG_NO_ACTUALIZADO} El correo ya está registrado por otro usuario")
    except RepositorioNoDisponibleError:
        return _respuesta(status.HTTP_503_SERVICE_UNAVAILABLE,
                          "No fue posible actualizar el perfil del cliente")
    return RespuestaPerfil(mensaje="Perfil actualizado correctamente", data=perfil, success=True)


# Se registra con add_api_route para usar la validación personalizada (400) solo en este endpoint
router.add_api_route(
    "/{usuario_id}",
    actualizar_perfil,
    methods=["PUT"],
    response_model=RespuestaPerfil,
    summary="Actualizar el perfil del cliente",
    route_class_override=PerfilValidacionRoute,
    responses={
        status.HTTP_200_OK: _ejemplo("Perfil actualizado correctamente", _EJEMPLO_PERFIL, True,
                                     "Perfil actualizado"),
        status.HTTP_400_BAD_REQUEST: _ejemplo(f"{MSG_NO_ACTUALIZADO} {MENSAJE_CORREO_INVALIDO}",
                                              None, False, "Datos inválidos"),
        status.HTTP_404_NOT_FOUND: _ejemplo(MSG_NO_EXISTE, _EJEMPLO_VACIO, False,
                                            "No existe el cliente"),
        status.HTTP_409_CONFLICT: _ejemplo(
            f"{MSG_NO_ACTUALIZADO} El correo ya está registrado por otro usuario", None, False,
            "Correo duplicado"),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo(
            "No fue posible actualizar el perfil del cliente", None, False,
            "Base de datos no disponible"),
    },
)
