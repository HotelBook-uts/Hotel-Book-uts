from typing import Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.api.habitacion_router import repo as habitacion_repo
from app.api.hotel_router import repo as hotel_repo
from app.api.usuario_router import repo as usuario_repo
from app.domain.errores import (FechasInvalidasError, HabitacionNoDisponibleError,
                                HabitacionNoEncontradaError, RepositorioNoDisponibleError,
                                ReservaNoEncontradaError, ReservaYaCanceladaError,
                                UsuarioNoEncontradoError)
from app.domain.reserva import (EstadoHistorial, HistorialReservas, ReservaCreate,
                                RespuestaCancelacion, RespuestaErrorReserva,
                                RespuestaHistorial, RespuestaReserva)
from app.repositories.reserva_repository import ReservaRepository
from app.service.reserva_service import ReservaService

# Se reutilizan los repositorios de habitaciones, usuarios y hoteles de sus routers,
# así todos los módulos comparten los mismos datos en memoria
repo = ReservaRepository()
service = ReservaService(repo, habitacion_repo, usuario_repo, hotel_repo)

router = APIRouter(prefix="/api/v1/reservas", tags=["Reservas"])

# HU-005: el historial cuelga de la ruta del usuario (/api/v1/usuarios/{id}/reservas)
historial_router = APIRouter(prefix="/api/v1/usuarios", tags=["Reservas"])

MSG_NO_DISPONIBLE = "La habitación no se encuentra disponible"
MSG_YA_CANCELADA = "La reserva ya se encuentra cancelada"


def _error(codigo: int, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=codigo,
                        content=RespuestaErrorReserva(mensaje=mensaje).model_dump())


def _ejemplo(modelo, ejemplo: dict, descripcion: str) -> dict:
    return {"model": modelo, "description": descripcion,
            "content": {"application/json": {"example": ejemplo}}}


@router.post(
    "/",
    response_model=RespuestaReserva,
    status_code=status.HTTP_201_CREATED,
    summary="Realizar una reserva de una habitación",
    responses={
        status.HTTP_201_CREATED: _ejemplo(
            RespuestaReserva,
            {"mensaje": "Reserva creada correctamente", "reservaId": 1, "success": True},
            "Reserva creada"),
        status.HTTP_400_BAD_REQUEST: _ejemplo(
            RespuestaErrorReserva,
            {"mensaje": MSG_NO_DISPONIBLE, "success": False},
            "La habitación no está disponible o las fechas no son válidas"),
        status.HTTP_404_NOT_FOUND: _ejemplo(
            RespuestaErrorReserva,
            {"mensaje": "La habitación indicada no existe", "success": False},
            "El cliente o la habitación no existen"),
    },
)
def crear_reserva(data: ReservaCreate):
    """HU-013: registra la reserva de una habitación para las fechas indicadas.

    Valida que la habitación exista, esté habilitada y no tenga otra reserva
    activa que se cruce con esas fechas. El día de salida de una reserva puede
    ser el día de entrada de otra.
    """
    try:
        reserva = service.crear(data)
    except HabitacionNoDisponibleError:
        return _error(status.HTTP_400_BAD_REQUEST, MSG_NO_DISPONIBLE)
    except FechasInvalidasError as exc:
        return _error(status.HTTP_400_BAD_REQUEST, str(exc))
    except HabitacionNoEncontradaError:
        return _error(status.HTTP_404_NOT_FOUND, "La habitación indicada no existe")
    except UsuarioNoEncontradoError:
        return _error(status.HTTP_404_NOT_FOUND, "El cliente indicado no existe")
    return RespuestaReserva(mensaje="Reserva creada correctamente",
                            reservaId=reserva.id, success=True)


@router.put(
    "/{reserva_id}",
    response_model=RespuestaCancelacion,
    summary="Cancelar una reserva registrada",
    responses={
        status.HTTP_200_OK: _ejemplo(
            RespuestaCancelacion,
            {"mensaje": "Reserva cancelada correctamente", "success": True},
            "Reserva cancelada"),
        status.HTTP_400_BAD_REQUEST: _ejemplo(
            RespuestaErrorReserva,
            {"mensaje": MSG_YA_CANCELADA, "success": False},
            "La reserva ya estaba cancelada"),
        status.HTTP_404_NOT_FOUND: _ejemplo(
            RespuestaErrorReserva,
            {"mensaje": "Reserva no encontrada", "success": False},
            "La reserva no existe"),
    },
)
def cancelar_reserva(reserva_id: int):
    """HU-014: cancela una reserva activa. La reserva pasa a estado "cancelada"
    y la habitación queda libre para esas fechas.
    """
    try:
        service.cancelar(reserva_id)
    except ReservaNoEncontradaError:
        return _error(status.HTTP_404_NOT_FOUND, "Reserva no encontrada")
    except ReservaYaCanceladaError:
        return _error(status.HTTP_400_BAD_REQUEST, MSG_YA_CANCELADA)
    return RespuestaCancelacion(mensaje="Reserva cancelada correctamente", success=True)


# ---------------------------------------------------------------------------
# HU-005: historial de reservas del cliente
# ---------------------------------------------------------------------------

MSG_HISTORIAL_OK = "Historial de reservas consultado"
MSG_SIN_RESERVAS = "El cliente no tiene reservas registradas"
MSG_CLIENTE_NO_EXISTE = "No existe un cliente con el identificador indicado"
MSG_HISTORIAL_503 = "No fue posible consultar el historial de reservas"

_EJEMPLO_HISTORIAL = {
    "usuarioId": 1024, "totalReservas": 2, "ultimaReserva": "RSV-2026-000148",
    "reservas": [
        {"reservaId": "RSV-2026-000148", "hotel": "Hotel Chicamocha",
         "fechaEntrada": "2026-12-12", "estado": "CONFIRMADA"},
        {"reservaId": "RSV-2026-000097", "hotel": "Hotel Ciudad Bonita",
         "fechaEntrada": "2026-08-02", "estado": "FINALIZADA"},
    ],
}


def _historial_vacio(usuario_id: int) -> dict:
    return HistorialReservas(usuarioId=usuario_id, totalReservas=0).model_dump(mode="json")


def _respuesta_historial(codigo: int, mensaje: str, data: Optional[dict]) -> JSONResponse:
    return JSONResponse(status_code=codigo,
                        content={"mensaje": mensaje, "data": data, "success": False})


@historial_router.get(
    "/{usuario_id}/reservas",
    response_model=RespuestaHistorial,
    summary="Consultar el historial de reservas del cliente",
    responses={
        status.HTTP_200_OK: _ejemplo(
            RespuestaHistorial,
            {"mensaje": MSG_HISTORIAL_OK, "data": _EJEMPLO_HISTORIAL, "success": True},
            "Historial consultado (si no hay reservas: success=false, totalReservas=0)"),
        status.HTTP_404_NOT_FOUND: _ejemplo(
            RespuestaHistorial,
            {"mensaje": MSG_CLIENTE_NO_EXISTE, "data": None, "success": False},
            "El cliente no existe"),
        status.HTTP_503_SERVICE_UNAVAILABLE: _ejemplo(
            RespuestaHistorial,
            {"mensaje": MSG_HISTORIAL_503, "data": None, "success": False},
            "Base de datos no disponible"),
    },
)
def historial_reservas(
    usuario_id: int,
    estado: Optional[EstadoHistorial] = Query(
        default=None, description="Filtro opcional: CONFIRMADA, FINALIZADA o CANCELADA"),
):
    """HU-005: muestra todas las reservas del cliente ordenadas por fecha de entrada
    (la más reciente primero), con el hotel y su estado.

    - **totalReservas**: total de reservas del cliente (según el filtro)
    - **ultimaReserva**: código de la reserva más reciente
    - **reservas**: listado con reservaId, hotel, fechaEntrada y estado

    Pendiente HU-002: un cliente solo podrá consultar sus propias reservas (403).
    """
    try:
        historial = service.historial(usuario_id, estado)
    except UsuarioNoEncontradoError:
        return _respuesta_historial(status.HTTP_404_NOT_FOUND, MSG_CLIENTE_NO_EXISTE, None)
    except RepositorioNoDisponibleError:
        return _respuesta_historial(status.HTTP_503_SERVICE_UNAVAILABLE, MSG_HISTORIAL_503, None)

    if historial.totalReservas == 0:
        return _respuesta_historial(status.HTTP_200_OK, MSG_SIN_RESERVAS,
                                    _historial_vacio(usuario_id))
    return RespuestaHistorial(mensaje=MSG_HISTORIAL_OK, data=historial, success=True)
