from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EstadoReserva(str, Enum):
    activa = "activa"
    cancelada = "cancelada"


# Lo que envía el cliente para RESERVAR (sin id)
class ReservaCreate(BaseModel):
    # TODO HU-002: el usuarioId se tomará de la sesión del cliente
    usuarioId: int = Field(..., gt=0, description="Identificador del cliente que reserva")
    habitacionId: int = Field(..., gt=0, description="Habitación que se desea reservar")
    fechaEntrada: date = Field(..., description="Fecha de llegada (AAAA-MM-DD)")
    fechaSalida: date = Field(..., description="Fecha de salida (AAAA-MM-DD)")

    model_config = ConfigDict(json_schema_extra={
        "example": {"usuarioId": 1, "habitacionId": 1,
                    "fechaEntrada": "2026-12-20", "fechaSalida": "2026-12-23"}
    })


# La reserva registrada (con id y estado)
class Reserva(ReservaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: EstadoReserva = EstadoReserva.activa

    # Regla de negocio: dos reservas se cruzan si comparten al menos una noche.
    # El día de salida de una puede ser el día de entrada de otra.
    def se_cruza_con(self, entrada: date, salida: date) -> bool:
        return self.fechaEntrada < salida and entrada < self.fechaSalida


# Formato de respuesta al crear la reserva: {mensaje, reservaId, success}
class RespuestaReserva(BaseModel):
    mensaje: str
    reservaId: Optional[int] = None
    success: bool


# Formato de respuesta de error: {mensaje, success}
class RespuestaErrorReserva(BaseModel):
    mensaje: str
    success: bool = False
