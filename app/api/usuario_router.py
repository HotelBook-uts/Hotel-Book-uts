from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencias import get_sesion, usuario_repo as repo
from app.api.validacion import ruta_validacion_400
from app.domain.auth import SesionUsuario
from app.domain.errores import (AccesoDenegadoError, CorreoDuplicadoError, RepositorioNoDisponibleError,
                                UsuarioNoEncontradoError)
from app.domain.usuario import (MENSAJE_CORREO_INVALIDO, PerfilUpdate, PerfilUsuario,
                                RespuestaPerfil, RespuestaRegistro, UsuarioCreate)
from app.service.usuario_service import UsuarioService

# El repositorio de usuarios es compartido con el login (HU-002), ver dependencias.py
service = UsuarioService(repo)

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


# ---------------------------------------------------------------------------
# HU-001: registro de usuario
# ---------------------------------------------------------------------------

MSG_REGISTRO_OK = "Usuario registrado correctamente"
MSG_NO_REGISTRADO = "No fue posible registrar el usuario."
MSG_CORREO_REGISTRADO = f"{MSG_NO_REGISTRADO} Ya existe un usuario registrado con ese correo"
MSG_REGISTRO_503 = "No fue posible registrar el usuario en este momento"


def _ejemplo_registro(codigo_desc: str, mensaje: str, data, success: bool) -> dict:
    return {"model": RespuestaRegistro, "description": codigo_desc,
            "content": {"application/json": {"example": {
                "mensaje": mensaje, "data": data, "success": success}}}}


def registrar_usuario(data: UsuarioCreate):
    """HU-001: registra un usuario nuevo como **CLIENTE** con la cuenta **ACTIVA**.

    - El correo se guarda en minúsculas y no puede repetirse.
    - La contraseña debe tener entre 8 y 72 caracteres, con al menos una letra y un número;
      se guarda cifrada y nunca se devuelve.
    """
    try:
        usuario = service.registrar(data)
    except CorreoDuplicadoError:
        return _respuesta_simple(status.HTTP_409_CONFLICT, MSG_CORREO_REGISTRADO)
    except RepositorioNoDisponibleError:
        return _respuesta_simple(status.HTTP_503_SERVICE_UNAVAILABLE, MSG_REGISTRO_503)
    return RespuestaRegistro(mensaje=MSG_REGISTRO_OK, data=usuario, success=True)


def _respuesta_simple(codigo: int, mensaje: str) -> JSONResponse:
    cuerpo = RespuestaRegistro(mensaje=mensaje, data=None, success=False)
    return JSONResponse(status_code=codigo, content=cuerpo.model_dump())


# Se registra con add_api_route para responder 400 (no 422) si los datos son inválidos
router.add_api_route(
    "/",
    registrar_usuario,
    methods=["POST"],
    response_model=RespuestaRegistro,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un usuario",
    route_class_override=ruta_validacion_400(MSG_NO_REGISTRADO),
    responses={
        status.HTTP_201_CREATED: _ejemplo_registro(
            "Usuario registrado", MSG_REGISTRO_OK,
            {"nombre": "Laura Gómez", "email": "laura.gomez@correo.com",
             "telefono": "3109876543", "id": 1}, True),
        status.HTTP_400_BAD_REQUEST: _ejemplo_registro(
            "Datos inválidos", f"{MSG_NO_REGISTRADO} {MENSAJE_CORREO_INVALIDO}", None, False),
        status.HTTP_409_CONFLICT: _ejemplo_registro(
            "Correo ya registrado", MSG_CORREO_REGISTRADO, None, False),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo_registro(
            "Base de datos no disponible", MSG_REGISTRO_503, None, False),
    },
)


# ---------------------------------------------------------------------------
# HU-004: consulta y actualización del perfil del cliente
# ---------------------------------------------------------------------------

MSG_NO_EXISTE = "No existe un cliente con el identificador indicado"
MSG_NO_ACTUALIZADO = "No fue posible actualizar el perfil."
MSG_403_CONSULTAR = ("No fue posible consultar el perfil. "
                     "Un cliente solo puede consultar su propio perfil")
MSG_403_ACTUALIZAR = f"{MSG_NO_ACTUALIZADO} Un cliente solo puede actualizar su propio perfil"


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


@router.get(
    "/{usuario_id}",
    response_model=RespuestaPerfil,
    summary="Consultar el perfil del cliente",
    responses={
        status.HTTP_200_OK: _ejemplo("Perfil consultado correctamente", _EJEMPLO_PERFIL, True,
                                     "Perfil encontrado"),
        status.HTTP_404_NOT_FOUND: _ejemplo(MSG_NO_EXISTE, _EJEMPLO_VACIO, False,
                                            "No existe el cliente"),
        status.HTTP_401_UNAUTHORIZED: {"description": "Sin sesión o token inválido/expirado"},
        status.HTTP_403_FORBIDDEN: _ejemplo(MSG_403_CONSULTAR, None, False, "Sin permiso"),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo(
            "No fue posible consultar el perfil del cliente", None, False,
            "Base de datos no disponible"),
    },
)
def consultar_perfil(usuario_id: int, sesion: SesionUsuario = Depends(get_sesion)):
    """HU-004: consulta el perfil del cliente (nombres, correo y teléfono) por su ID,
    sin exponer datos sensibles.

    Requiere sesión (HU-002): solo el dueño del perfil o un administrador.
    """
    try:
        perfil = service.consultar_perfil(usuario_id, sesion)
    except AccesoDenegadoError:
        return _respuesta(status.HTTP_403_FORBIDDEN, MSG_403_CONSULTAR)
    except UsuarioNoEncontradoError:
        return _respuesta(status.HTTP_404_NOT_FOUND, MSG_NO_EXISTE, _perfil_vacio(usuario_id))
    except RepositorioNoDisponibleError:
        return _respuesta(status.HTTP_503_SERVICE_UNAVAILABLE,
                          "No fue posible consultar el perfil del cliente")
    return RespuestaPerfil(mensaje="Perfil consultado correctamente", data=perfil, success=True)


def actualizar_perfil(usuario_id: int, data: PerfilUpdate,
                      sesion: SesionUsuario = Depends(get_sesion)):
    """HU-004: actualiza los datos de contacto del cliente (nombres, correo y teléfono).
    El correo debe tener formato válido y no puede pertenecer a otro usuario.

    Requiere sesión (HU-002): solo el dueño del perfil o un administrador.
    """
    try:
        perfil = service.actualizar_perfil(usuario_id, data, sesion)
    except AccesoDenegadoError:
        return _respuesta(status.HTTP_403_FORBIDDEN, MSG_403_ACTUALIZAR)
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
    route_class_override=ruta_validacion_400(MSG_NO_ACTUALIZADO),
    responses={
        status.HTTP_200_OK: _ejemplo("Perfil actualizado correctamente", _EJEMPLO_PERFIL, True,
                                     "Perfil actualizado"),
        status.HTTP_400_BAD_REQUEST: _ejemplo(f"{MSG_NO_ACTUALIZADO} {MENSAJE_CORREO_INVALIDO}",
                                              None, False, "Datos inválidos"),
        status.HTTP_404_NOT_FOUND: _ejemplo(MSG_NO_EXISTE, _EJEMPLO_VACIO, False,
                                            "No existe el cliente"),
        status.HTTP_401_UNAUTHORIZED: {"description": "Sin sesión o token inválido/expirado"},
        status.HTTP_403_FORBIDDEN: _ejemplo(MSG_403_ACTUALIZAR, None, False, "Sin permiso"),
        status.HTTP_409_CONFLICT: _ejemplo(
            f"{MSG_NO_ACTUALIZADO} El correo ya está registrado por otro usuario", None, False,
            "Correo duplicado"),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo(
            "No fue posible actualizar el perfil del cliente", None, False,
            "Base de datos no disponible"),
    },
)
