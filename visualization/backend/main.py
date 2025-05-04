from fastapi import FastAPI
from fastapi import Request
import hashlib
from visualization.backend.db.config import settings
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine
from visualization.backend.db.database import Base
from visualization.backend.api.routers.components import router as components_router




DATABASE_URL = (
    settings.DATABASE_URL
) 

engine = create_async_engine(DATABASE_URL, echo=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация: создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Завершение: удаление всех таблиц при завершении работы приложения
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


app = FastAPI(lifespan=lifespan)

app.include_router(components_router)
