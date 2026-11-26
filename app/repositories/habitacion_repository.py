from typing import List, Optional

from app.domain.habitacion import Habitacion, HabitacionCreate


class HabitacionRepository:
    """Base de datos simulada en memoria."""

    def __init__(self):
        self._db: dict[int, Habitacion] = {}
        self._next_id: int = 1

    def get_all(
        self,
        hotel_id: Optional[int] = None,
        disponible: Optional[bool] = None,
    ) -> List[Habitacion]:
        habitaciones = list(self._db.values())
        if hotel_id is not None:
            habitaciones = [h for h in habitaciones if h.hotel_id == hotel_id]
        if disponible is not None:
            habitaciones = [h for h in habitaciones if h.disponible == disponible]
        return habitaciones

    def get_by_id(self, habitacion_id: int) -> Optional[Habitacion]:
        return self._db.get(habitacion_id)

    def get_by_hotel_numero(self, hotel_id: int, numero: str) -> Optional[Habitacion]:
        return next(
            (h for h in self._db.values()
             if h.hotel_id == hotel_id and h.numero == numero),
            None,
        )

    def create(self, data: HabitacionCreate) -> Habitacion:
        habitacion = Habitacion(id=self._next_id, **data.model_dump())
        self._db[self._next_id] = habitacion
        self._next_id += 1
        return habitacion

    def update(self, habitacion_id: int, data: HabitacionCreate) -> Optional[Habitacion]:
        if habitacion_id not in self._db:
            return None
        habitacion = Habitacion(id=habitacion_id, **data.model_dump())
        self._db[habitacion_id] = habitacion
        return habitacion

    def delete(self, habitacion_id: int) -> bool:
        if habitacion_id in self._db:
            del self._db[habitacion_id]
            return True
        return False