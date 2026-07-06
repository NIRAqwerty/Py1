from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import SqlAlchemyUserRepository
from src.infrastructure.security import decode_access_token
from src.domain.entities import User
from src.infrastructure.ai.orchestrator import AIOrchestrator

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_ai_orchestrator = AIOrchestrator()

def get_ai_orchestrator() -> AIOrchestrator:
    return _ai_orchestrator

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
        
    user_repo = SqlAlchemyUserRepository(session)
    user = await user_repo.find_by_username(username)
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your user role."
            )
        return current_user
