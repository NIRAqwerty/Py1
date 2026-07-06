import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import SqlAlchemySourceRepository
from src.api.dependencies import get_current_user, RoleChecker
from src.domain.entities import Source, User
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["config"])

allow_admins = RoleChecker(allowed_roles=["ADMIN"])

class SourceCreate(BaseModel):
    name: str
    type: str  # "TELEGRAM", etc.
    config: dict

@router.post("/sources", status_code=status.HTTP_201_CREATED)
async def add_source(
    data: SourceCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(allow_admins)
) -> dict:
    repo = SqlAlchemySourceRepository(session)
    source = Source(
        id=uuid.uuid4(),
        name=data.name,
        type=data.type,
        config=data.config,
        status="ACTIVE"
    )
    await repo.save(source)
    await session.commit()
    return {"message": "Source added successfully", "source_id": str(source.id)}
