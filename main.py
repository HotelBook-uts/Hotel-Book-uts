from fastapi import FastAPI
from app.api.hotel_router import router as hotel_router

app = FastAPI(
    title="Hotel-Book",
    description="Web Service para la gestión de reservas de hotel",
    version="1.0.0"
)
app.include_router(hotel_router)


@app.get("/")
def inicio():
    return {"mensaje": "Web Service funcionando correctamente"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
