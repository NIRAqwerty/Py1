import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from src.config import settings
from src.api.v1.router import api_v1_router
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.database.models import UserModel
from src.infrastructure.security import get_password_hash
from src.infrastructure.logging import get_logger
from src.infrastructure.monitoring import setup_monitoring
from src.infrastructure.telegram.bot import start_bot, stop_bot

logger = get_logger("GENERAL")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up FastAPI application")
    
    # Start Telegram Management Bot
    start_bot()
    
    async with async_session_maker() as session:
        try:
            stmt = select(UserModel).limit(1)
            res = await session.execute(stmt)
            exists = res.scalar_one_or_none()
            
            if not exists:
                logger.info("No users found. Seeding default admin and operator users.")
                admin = UserModel(
                    id=uuid.uuid4(),
                    username="admin",
                    hashed_password=get_password_hash("admin123"),
                    role="ADMIN"
                )
                operator = UserModel(
                    id=uuid.uuid4(),
                    username="operator",
                    hashed_password=get_password_hash("operator123"),
                    role="OPERATOR"
                )
                session.add(admin)
                session.add(operator)
                await session.commit()
                logger.info(
                    "Default users seeded.",
                    admin="admin/admin123",
                    operator="operator/operator123",
                )
        except Exception as e:
            logger.error("Failed to seed default users on startup", error=str(e))
    yield
    logger.info("Shutting down FastAPI application")
    # Stop Telegram Management Bot
    await stop_bot()

app = FastAPI(
    title=settings.app.name,
    description="Production-Ready AI Telegram Channel Publisher API",
    version="1.0.0",
    docs_url="/docs" if settings.app.env == "development" or settings.app.debug else None,
    lifespan=lifespan,
)

# Setup Prometheus metrics exporter
setup_monitoring(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)
