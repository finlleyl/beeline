from fastapi import FastAPI
from visualization.backend.api.routers.components import router as components_router
from fastapi import Request
import hashlib
from visualization.backend.db.config import settings
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine
from visualization.backend.db.database import Base

app = FastAPI(
    title="Beeline case"
)

app.include_router(components_router)


DATABASE_URL = (
    settings.DATABASE_URL
)  # Убедитесь, что это асинхронный URL, например, "postgresql+asyncpg://..."

engine = create_async_engine(DATABASE_URL, echo=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация: создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Завершение: здесь можно добавить логику очистки ресурсов, если необходимо


app = FastAPI(lifespan=lifespan)
