from typing import List, Optional

from fastapi import APIRouter, status

from app.domain.hotel import Hotel, HotelCreate
from app.repositories.hotel_repository import HotelRepository
from app.service.hotel_service import HotelService

# Instancias: un solo repositorio, así los datos se comparten entre peticiones
repo = HotelRepository()
service = HotelService(repo)

router = APIRouter(prefix="/hoteles", tags=["Hoteles"])


@router.get("/", response_model=List[Hotel])
def listar_hoteles(ciudad: Optional[str] = None):
    """Lista los hoteles. Con ?ciudad=Bucaramanga filtra por ciudad."""
    return service.listar(ciudad)


@router.get("/{hotel_id}", response_model=Hotel)
def obtener_hotel(hotel_id: int):
    """HU-007: consulta un hotel por su ID."""
    return service.obtener(hotel_id)


@router.post("/", response_model=Hotel, status_code=status.HTTP_201_CREATED)
def crear_hotel(data: HotelCreate):
    """HU-006: registra un hotel nuevo."""
    return service.crear(data)


@router.put("/{hotel_id}", response_model=Hotel)
def actualizar_hotel(hotel_id: int, data: HotelCreate):
    """HU-011: actualiza todos los datos de un hotel."""
    return service.actualizar(hotel_id, data)


@router.delete("/{hotel_id}")
def eliminar_hotel(hotel_id: int):
    """Elimina un hotel por su ID."""
    return service.eliminar(hotel_id)
