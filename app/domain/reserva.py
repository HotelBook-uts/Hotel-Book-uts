from datetime import date
from enum import Enum
from typing import List, Optional

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


# HU-005: estado de la reserva tal como lo ve el cliente en su historial
class EstadoHistorial(str, Enum):
    CONFIRMADA = "CONFIRMADA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


# La reserva registrada (con id y estado)
class Reserva(ReservaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: EstadoReserva = EstadoReserva.activa
    fechaCreacion: date = Field(default_factory=date.today)

    # Regla de negocio: dos reservas se cruzan si comparten al menos una noche.
    # El día de salida de una puede ser el día de entrada de otra.
    def se_cruza_con(self, entrada: date, salida: date) -> bool:
        return self.fechaEntrada < salida and entrada < self.fechaSalida

    # HU-005: código visible de la reserva, ej. RSV-2026-000148
    @property
    def codigo(self) -> str:
        return f"RSV-{self.fechaCreacion.year}-{self.id:06d}"

    # HU-005: una reserva activa queda FINALIZADA cuando ya pasó su fecha de salida
    def estado_historial(self, hoy: date) -> EstadoHistorial:
        if self.estado == EstadoReserva.cancelada:
            return EstadoHistorial.CANCELADA
        if self.fechaSalida < hoy:
            return EstadoHistorial.FINALIZADA
        return EstadoHistorial.CONFIRMADA


# Formato de respuesta al crear la reserva: {mensaje, reservaId, success}
class RespuestaReserva(BaseModel):
    mensaje: str
    reservaId: Optional[int] = None
    success: bool


# HU-014: formato de respuesta al cancelar: {mensaje, success}
class RespuestaCancelacion(BaseModel):
    mensaje: str
    success: bool


# HU-005: una reserva dentro del historial del cliente
class ReservaHistorial(BaseModel):
    reservaId: str
    hotel: str
    fechaEntrada: date
    estado: EstadoHistorial


# HU-005: historial de reservas del cliente
class HistorialReservas(BaseModel):
    usuarioId: int
    totalReservas: int
    ultimaReserva: Optional[str] = None
    reservas: List[ReservaHistorial] = []


# HU-005: formato de respuesta del historial: {mensaje, data, success}
class RespuestaHistorial(BaseModel):
    mensaje: str
    data: Optional[HistorialReservas] = None
    success: bool


# Formato de respuesta de error: {mensaje, success}
class RespuestaErrorReserva(BaseModel):
    mensaje: str
    success: bool = False
