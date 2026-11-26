import json

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencias import auth_service, get_sesion
from app.api.validacion import respuesta_error, ruta_validacion_400
from app.core.config import settings
from app.domain.auth import DatosSesion, LoginRequest, RespuestaAuth, RespuestaLogin, SesionUsuario
from app.domain.errores import (CredencialesInvalidasError, CuentaBloqueadaError,
                                CuentaNoActivaError, RepositorioNoDisponibleError)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

MSG_LOGIN_OK = "Inicio de sesión exitoso"
MSG_NO_ACTIVA = "No existe una cuenta activa con el correo indicado"
MSG_BLOQUEADA = ("La cuenta está bloqueada por superar el máximo de intentos fallidos. "
                 "Comuníquese con el administrador")
MSG_LOGIN_400 = "No fue posible iniciar sesión."
MSG_LOGIN_503 = "No fue posible iniciar la sesión"


def _sin_sesion(correo: str) -> dict:
    return DatosSesion(correo=correo).model_dump(mode="json")


async def _correo_del_cuerpo(request: Request) -> dict:
    # En el 400 se devuelve el correo que se envió, con token/rol/expiraEn en null
    try:
        correo = json.loads(await request.body()).get("correo")
    except (ValueError, AttributeError):
        correo = None
    return {"correo": correo, "token": None, "rol": None, "expiraEn": None}


def _ejemplo(mensaje: str, data, success: bool, descripcion: str, modelo=RespuestaLogin) -> dict:
    return {"model": modelo, "description": descripcion,
            "content": {"application/json": {"example": {
                "mensaje": mensaje, **({"data": data} if data is not ... else {}),
                "success": success}}}}


_DATOS_OK = {"correo": "laura.gomez@correo.com",
             "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOjEwMjR9.firma",
             "rol": "CLIENTE", "expiraEn": "2026-11-09T18:00:00Z"}
_DATOS_VACIOS = {"correo": "sin.cuenta@correo.com", "token": None, "rol": None, "expiraEn": None}


def login(data: LoginRequest):
    """HU-002: inicia sesión con correo y contraseña y entrega un token JWT con el rol.

    - Registra cada intento en **intentos_acceso**.
    - Al fallar la contraseña **{max}** veces seguidas, la cuenta queda **BLOQUEADA**.
    - El token se envía en las demás peticiones con el header
      `Authorization: Bearer <token>` (botón **Authorize** en Swagger).
    """
    try:
        sesion = auth_service.login(data)
    except CuentaNoActivaError:
        return respuesta_error(status.HTTP_401_UNAUTHORIZED, MSG_NO_ACTIVA, _sin_sesion(data.correo))
    except CredencialesInvalidasError as exc:
        return respuesta_error(
            status.HTTP_401_UNAUTHORIZED,
            f"Correo o contraseña incorrectos. Intentos restantes: {exc.intentos_restantes}",
            _sin_sesion(data.correo))
    except CuentaBloqueadaError:
        return respuesta_error(status.HTTP_403_FORBIDDEN, MSG_BLOQUEADA, _sin_sesion(data.correo))
    except RepositorioNoDisponibleError:
        return respuesta_error(status.HTTP_503_SERVICE_UNAVAILABLE, MSG_LOGIN_503,
                               _sin_sesion(data.correo))
    return RespuestaLogin(mensaje=MSG_LOGIN_OK, data=sesion, success=True)


login.__doc__ = login.__doc__.replace("{max}", str(settings.MAX_INTENTOS_FALLIDOS))

# Se registra con add_api_route para responder 400 (no 422) si el correo es inválido
router.add_api_route(
    "/login",
    login,
    methods=["POST"],
    response_model=RespuestaLogin,
    summary="Iniciar sesión",
    route_class_override=ruta_validacion_400(MSG_LOGIN_400, _correo_del_cuerpo),
    responses={
        status.HTTP_200_OK: _ejemplo(MSG_LOGIN_OK, _DATOS_OK, True, "Sesión iniciada"),
        status.HTTP_400_BAD_REQUEST: _ejemplo(
            "No fue posible iniciar sesión. Formato de correo no válido. Debe ser usuario@dominio.com",
            {**_DATOS_VACIOS, "correo": "laura.gomez"}, False, "Datos inválidos"),
        status.HTTP_401_UNAUTHORIZED: _ejemplo(MSG_NO_ACTIVA, _DATOS_VACIOS, False,
                                               "Cuenta inexistente/inactiva o contraseña incorrecta"),
        status.HTTP_403_FORBIDDEN: _ejemplo(MSG_BLOQUEADA, {**_DATOS_OK, "token": None, "rol": None,
                                                            "expiraEn": None},
                                            False, "Cuenta bloqueada"),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo(MSG_LOGIN_503, _DATOS_VACIOS, False,
                                                      "Base de datos no disponible"),
    },
)


@router.post(
    "/logout",
    response_model=RespuestaAuth,
    summary="Cerrar sesión",
    responses={
        status.HTTP_200_OK: _ejemplo("Sesión cerrada correctamente", ..., True,
                                     "Sesión cerrada", RespuestaAuth),
        status.HTTP_401_UNAUTHORIZED: _ejemplo(
            "Sesión no válida o expirada. Inicie sesión nuevamente", None, False,
            "Token inválido, expirado o ya cerrado"),
    },
)
def logout(sesion: SesionUsuario = Depends(get_sesion)):
    """HU-002: cierra la sesión. El token enviado queda invalidado y no se puede volver a usar."""
    auth_service.logout(sesion)
    return RespuestaAuth(mensaje="Sesión cerrada correctamente", success=True)
