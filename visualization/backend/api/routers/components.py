import shutil
import tempfile
import zipfile
import aiofiles
from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import httpx

from llm.generate import generate_docs, generate_module_docs, generate_overview_docs, zip_docs


router = APIRouter(prefix="/components", tags=["components"])


@router.post("/upload_and_extract/")
async def upload_and_extract(
    zip_file: bytes = Body(..., media_type="application/zip")
) -> FileResponse:
    """
    Получаем ZIP в теле запроса (Content-Type: application/zip),
    и возвращаем docs_upd.zip из корня проекта
    """
    try:
        # Очищаем папку content перед обработкой
        content_dir = Path(__file__).parent.parent.parent.parent.parent / "content"
        if content_dir.exists():
            shutil.rmtree(content_dir)
        content_dir.mkdir()
        # Путь к ZIP-файлу в корне проекта
        # zip_path = Path(__file__).parent.parent.parent.parent.parent / "docs_upd.zip"
        generate_docs(zip_file)

        generate_module_docs()

        generate_overview_docs()

        filepath = zip_docs()

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="docs_upd.zip не найден")

        return FileResponse(
            path=filepath, filename="docs_upd.zip", media_type="application/zip"
        )
        
        
        # filepath = Path('C:/project/beeline/docs_upd.zip')

        # if not filepath.exists():
        #     raise HTTPException(status_code=404, detail="docs_upd.zip не найден")

        # return FileResponse(
        #     path=filepath, filename="docs_upd.zip", media_type="application/zip"
        # )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/download_and_extract/")
# async def download_and_extract(
#     repo_url: str = Query(..., description="HTTPS-ссылка на GitHub-репозиторий"),
#     branch: str = Query("main", description="Ветка или тег"),
# ):
#     # # 4.1) Сохраняем или вытягиваем Repository
#     # async with AsyncSessionLocal() as session:
#     #     # пытаемся найти уже существующую запись
#     #     result = await session.execute(
#     #         "SELECT id FROM repositories WHERE url = :url", {"url": repo_url}
#     #     )
#     #     row = result.first()
#     #     if row:
#     #         repo_id = row[0]
#     #     else:
#     #         # вставляем новую
#     #         result = await session.execute(
#     #             "INSERT INTO repositories (url) VALUES (:url) RETURNING id",
#     #             {"url": repo_url},
#     #         )
#     #         repo_id = result.scalar_one()
#     #         await session.commit()

#     # 4.2) Скачиваем ZIP
#     zip_url = repo_url.rstrip("/") + f"/zipball/{branch}"
#     async with httpx.AsyncClient(timeout=60) as client:
#         resp = await client.get(zip_url)
#         if resp.status_code != 200:
#             raise HTTPException(
#                 status_code=resp.status_code, detail="Не удалось скачать ZIP"
#             )
#     # 4.3) Сохраняем и распаковываем
#     tmp = Path(tempfile.gettempdir())
#     zip_path = tmp / f"{"1"}.zip"
#     async with aiofiles.open(zip_path, "wb") as f:
#         await f.write(resp.content)
#     extract_dir = tmp / f"repo_{"1"}"
#     extract_dir.mkdir(exist_ok=True)
#     with zipfile.ZipFile(zip_path, "r") as z:
#         z.extractall(extract_dir)

#     return JSONResponse({"repo_id": "1", "extracted_to": str(extract_dir)})
