from fastapi import APIRouter, Request, WebSocket

from visualization.backend.main import make_fingerprint





router = APIRouter(prefix="/components", tags=["components"])


@router.get("")
async def get_visualizatioin():
    return pass


