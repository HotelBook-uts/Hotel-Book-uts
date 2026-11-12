from pydantic import BaseModel, ConfigDict, Field, field_validator


class HotelBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    ciudad: str = Field(..., min_length=2, max_length=60)
    direccion: str = Field(..., min_length=5, max_length=150)
    estrellas: int = Field(..., ge=1, le=5)
    precio_noche: float = Field(..., gt=0)

    # Regla de negocio: limpiar espacios y dar formato al nombre y la ciudad
    @field_validator("nombre", "ciudad")
    @classmethod
    def limpiar_texto(cls, v: str) -> str:
        return v.strip().title()

    # Regla de negocio: precio con máximo dos decimales
    @field_validator("precio_noche")
    @classmethod
    def redondear_precio(cls, v: float) -> float:
        return round(v, 2)


# Lo que envía el cliente para CREAR un hotel (sin id)
class HotelCreate(HotelBase):
    pass


# Lo que devuelve la API (con id)
class Hotel(HotelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
