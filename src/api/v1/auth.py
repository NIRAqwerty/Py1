import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import SqlAlchemyUserRepository
from src.infrastructure.security import verify_password, create_access_token, get_password_hash
from src.domain.entities import User
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegister(BaseModel):
    username: str
    password: str
    role: str = "OPERATOR"  # "ADMIN" or "OPERATOR"

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, session: AsyncSession = Depends(get_db_session)) -> dict:
    repo = SqlAlchemyUserRepository(session)
    existing = await repo.find_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed = get_password_hash(data.password)
    user = User(
        id=uuid.uuid4(),
        username=data.username,
        hashed_password=hashed,
        role=data.role
    )
    await repo.save(user)
    await session.commit()
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    repo = SqlAlchemyUserRepository(session)
    user = await repo.find_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
        
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
