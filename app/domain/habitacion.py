from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TipoHabitacion(str, Enum):
    sencilla = "sencilla"
    doble = "doble"
    suite = "suite"


class HabitacionBase(BaseModel):
    hotel_id: int = Field(..., gt=0)
    numero: str = Field(..., min_length=1, max_length=10)
    tipo: TipoHabitacion
    capacidad: int = Field(..., ge=1, le=10)
    precio_noche: float = Field(..., gt=0)
    disponible: bool = True

    # Regla de negocio: el número de habitación no lleva espacios
    @field_validator("numero")
    @classmethod
    def limpiar_numero(cls, v: str) -> str:
        return v.strip().upper()

    # Regla de negocio: precio con máximo dos decimales
    @field_validator("precio_noche")
    @classmethod
    def redondear_precio(cls, v: float) -> float:
        return round(v, 2)


# Lo que envía el cliente para CREAR (sin id)
class HabitacionCreate(HabitacionBase):
    pass


# Lo que devuelve la API (con id)
class Habitacion(HabitacionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
