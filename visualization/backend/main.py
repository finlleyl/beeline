from fastapi import FastAPI
from visualization.backend.api.routers.components import router as components_router
from fastapi import Request
import hashlib

app = FastAPI(
    title="Beeline case"
)

app.include_router(components_router)





def make_fingerprint(request: Request) -> str:
    # собираем базовые параметры
    ip = request.client.host
    ua = request.headers.get("user-agent", "")
    lang = request.headers.get("accept-language", "")
    # объединяем в одну строку
    raw = f"{ip}|{ua}|{lang}"
    # вычисляем SHA-256
    return hashlib.sha256(raw.encode()).hexdigest()



