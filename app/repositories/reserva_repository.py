from datetime import date
from typing import List, Optional

from app.domain.reserva import EstadoReserva, Reserva, ReservaCreate


class ReservaRepository:
    """Base de datos simulada en memoria."""

    def __init__(self):
        self._db: dict[int, Reserva] = {}
        self._next_id: int = 1

    def get_by_id(self, reserva_id: int) -> Optional[Reserva]:
        return self._db.get(reserva_id)

    def get_activas_que_se_cruzan(
        self, habitacion_id: int, entrada: date, salida: date
    ) -> List[Reserva]:
        return [
            r for r in self._db.values()
            if r.habitacionId == habitacion_id
            and r.estado == EstadoReserva.activa
            and r.se_cruza_con(entrada, salida)
        ]

    def create(self, data: ReservaCreate) -> Reserva:
        reserva = Reserva(id=self._next_id, **data.model_dump())
        self._db[self._next_id] = reserva
        self._next_id += 1
        return reserva
