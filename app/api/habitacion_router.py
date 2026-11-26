from typing import List, Optional

from fastapi import APIRouter, status

from app.api.hotel_router import repo as hotel_repo
from app.domain.habitacion import Habitacion, HabitacionCreate
from app.repositories.habitacion_repository import HabitacionRepository
from app.service.habitacion_service import HabitacionService

# Se reutiliza el repositorio de hoteles del otro router,
# así ambos módulos comparten los mismos datos en memoria
repo = HabitacionRepository()
service = HabitacionService(repo, hotel_repo)

router = APIRouter(prefix="/habitaciones", tags=["Habitaciones"])


@router.get("/", response_model=List[Habitacion])
def listar_habitaciones(hotel_id: Optional[int] = None, disponible: Optional[bool] = None):
    """HU-009: lista habitaciones. Filtros opcionales: ?hotel_id=1 y ?disponible=true."""
    return service.listar(hotel_id, disponible)


@router.get("/{habitacion_id}", response_model=Habitacion)
def obtener_habitacion(habitacion_id: int):
    """HU-010: consulta una habitación por su ID."""
    return service.obtener(habitacion_id)


@router.post("/", response_model=Habitacion, status_code=status.HTTP_201_CREATED)
def crear_habitacion(data: HabitacionCreate):
    """HU-008: registra una habitación en un hotel existente."""
    return service.crear(data)


@router.put("/{habitacion_id}", response_model=Habitacion)
def actualizar_habitacion(habitacion_id: int, data: HabitacionCreate):
    """HU-012: actualiza los datos de una habitación."""
    return service.actualizar(habitacion_id, data)


@router.delete("/{habitacion_id}")
def eliminar_habitacion(habitacion_id: int):
    """HU-012: elimina una habitación."""
    return service.eliminar(habitacion_id)