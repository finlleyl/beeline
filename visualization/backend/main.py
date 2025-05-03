from fastapi import FastAPI
from visualization.backend.api.routers.components import router as components_router
from fastapi import Request
import hashlib
from fastapi import FastAPI

app = FastAPI(
    title="Beeline case"
)

app.include_router(components_router)
