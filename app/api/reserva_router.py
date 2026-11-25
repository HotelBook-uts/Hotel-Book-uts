from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.habitacion_router import repo as habitacion_repo
from app.api.usuario_router import repo as usuario_repo
from app.domain.errores import (FechasInvalidasError, HabitacionNoDisponibleError,
                                HabitacionNoEncontradaError, ReservaNoEncontradaError,
                                ReservaYaCanceladaError, UsuarioNoEncontradoError)
from app.domain.reserva import (ReservaCreate, RespuestaCancelacion, RespuestaErrorReserva,
                                RespuestaReserva)
from app.repositories.reserva_repository import ReservaRepository
from app.service.reserva_service import ReservaService

# Se reutilizan los repositorios de habitaciones y usuarios de sus routers,
# así todos los módulos comparten los mismos datos en memoria
repo = ReservaRepository()
service = ReservaService(repo, habitacion_repo, usuario_repo)

router = APIRouter(prefix="/api/v1/reservas", tags=["Reservas"])

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
