from typing import List, Optional

from fastapi import HTTPException, status

from app.domain.habitacion import Habitacion, HabitacionCreate
from app.repositories.habitacion_repository import HabitacionRepository
from app.repositories.hotel_repository import HotelRepository


class HabitacionService:
    def __init__(self, repo: HabitacionRepository, hotel_repo: HotelRepository):
        # Inyección de dependencias: recibe ambos repositorios
        self.repo = repo
        self.hotel_repo = hotel_repo

    def _validar_hotel(self, hotel_id: int) -> None:
        # Regla de negocio: la habitación debe pertenecer a un hotel que exista
        if not self.hotel_repo.get_by_id(hotel_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El hotel {hotel_id} no existe",
            )

    def listar(
        self,
        hotel_id: Optional[int] = None,
        disponible: Optional[bool] = None,
    ) -> List[Habitacion]:
        return self.repo.get_all(hotel_id, disponible)

    def obtener(self, habitacion_id: int) -> Habitacion:
        habitacion = self.repo.get_by_id(habitacion_id)
        if not habitacion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Habitación {habitacion_id} no encontrada",
            )
        return habitacion

    def crear(self, data: HabitacionCreate) -> Habitacion:
        self._validar_hotel(data.hotel_id)

        # Regla de negocio: no repetir el número de habitación dentro del mismo hotel
        if self.repo.get_by_hotel_numero(data.hotel_id, data.numero):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El hotel {data.hotel_id} ya tiene una habitación {data.numero}",
            )
        return self.repo.create(data)

    def actualizar(self, habitacion_id: int, data: HabitacionCreate) -> Habitacion:
        self.obtener(habitacion_id)  # lanza 404 si no existe
        self._validar_hotel(data.hotel_id)

        # El número no puede coincidir con OTRA habitación del mismo hotel
        existente = self.repo.get_by_hotel_numero(data.hotel_id, data.numero)
        if existente and existente.id != habitacion_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El hotel {data.hotel_id} ya tiene una habitación {data.numero}",
            )
        return self.repo.update(habitacion_id, data)

    def eliminar(self, habitacion_id: int) -> dict:
        if not self.repo.delete(habitacion_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Habitación {habitacion_id} no encontrada",
            )
        return {"message": "Habitación eliminada correctamente"}
