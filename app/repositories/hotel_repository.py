from typing import List, Optional

from app.domain.hotel import Hotel, HotelCreate


class HotelRepository:
    """Base de datos simulada en memoria."""

    def __init__(self):
        self._db: dict[int, Hotel] = {}
        self._next_id: int = 1

    def get_all(self, ciudad: Optional[str] = None) -> List[Hotel]:
        hoteles = list(self._db.values())
        if ciudad:
            hoteles = [h for h in hoteles if h.ciudad.lower() ==
                       ciudad.lower()]
        return hoteles

    def get_by_id(self, hotel_id: int) -> Optional[Hotel]:
        return self._db.get(hotel_id)

    def get_by_nombre_ciudad(self, nombre: str, ciudad: str) -> Optional[Hotel]:
        return next(
            (h for h in self._db.values()
             if h.nombre.lower() == nombre.lower() and h.ciudad.lower() == ciudad.lower()),
            None,
        )

    def create(self, data: HotelCreate) -> Hotel:
        hotel = Hotel(id=self._next_id, **data.model_dump())
        self._db[self._next_id] = hotel
        self._next_id += 1
        return hotel

    def update(self, hotel_id: int, data: HotelCreate) -> Optional[Hotel]:
        if hotel_id not in self._db:
            return None
        hotel = Hotel(id=hotel_id, **data.model_dump())
        self._db[hotel_id] = hotel
        return hotel

    def delete(self, hotel_id: int) -> bool:
        if hotel_id in self._db:
            del self._db[hotel_id]
            return True
        return False
