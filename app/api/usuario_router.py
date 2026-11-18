from fastapi import APIRouter, status

from app.domain.usuario import Usuario, UsuarioCreate
from app.repositories.usuario_repository import UsuarioRepository
from app.service.usuario_service import UsuarioService

# Instancias: un solo repositorio, así los datos se comparten entre peticiones
repo = UsuarioRepository()
service = UsuarioService(repo)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def registrar_usuario(data: UsuarioCreate):
    """HU-001: registra un usuario nuevo."""
    return service.registrar(data)