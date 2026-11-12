from typing import List, Optional

from fastapi import HTTPException, status

from app.domain.hotel import Hotel, HotelCreate
from app.repositories.hotel_repository import HotelRepository


class HotelService:
    def __init__(self, repo: HotelRepository):
        # Inyección de dependencias: recibe el repositorio, no lo crea
        self.repo = repo

    def listar(self, ciudad: Optional[str] = None) -> List[Hotel]:
        return self.repo.get_all(ciudad)

    def obtener(self, hotel_id: int) -> Hotel:
        hotel = self.repo.get_by_id(hotel_id)
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hotel {hotel_id} no encontrado",
            )
        return hotel

    def crear(self, data: HotelCreate) -> Hotel:
        # Regla de negocio: no repetir el mismo hotel en la misma ciudad
        if self.repo.get_by_nombre_ciudad(data.nombre, data.ciudad):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un hotel con ese nombre en esa ciudad",
            )
        return self.repo.create(data)

    def actualizar(self, hotel_id: int, data: HotelCreate) -> Hotel:
        hotel = self.repo.update(hotel_id, data)
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hotel {hotel_id} no encontrado",
            )
        return hotel

    def eliminar(self, hotel_id: int) -> dict:
        if not self.repo.delete(hotel_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hotel {hotel_id} no encontrado",
            )
        return {"message": "Hotel eliminado correctamente"}
