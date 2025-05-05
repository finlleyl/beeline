from __future__ import annotations
import zipfile
from yandex_cloud_ml_sdk import YCloudML
import os
from pathlib import Path
import requests, json
from pathlib import Path
import shutil


API_KEY = os.getenv("api_key")
FOLDER_ID = os.getenv("folder")
URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


model_uri = f"gpt://{FOLDER_ID}/yandexgpt-32k/latest"
MODEL_URI = f"gpt://{FOLDER_ID}/yandexgpt-32k/latest"


output_dir = "/content/generated_docs"
os.makedirs(output_dir, exist_ok=True)


def unzip_bytes_to_dir(zip_bytes: bytes, extract_path: str) -> None:
    """
    Extracts zip archive from bytes to specified path
    """
    temp_zip = Path(extract_path) / "temp.zip"
    temp_zip.write_bytes(zip_bytes)

    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    temp_zip.unlink()  # Remove temporary zip file


def collect_python_files(repo_path: str) -> list[str]:
    """
    собирает все .py-файлы
    """
    py_files = []
    for root, _, files in os.walk(repo_path):
        for fn in files:
            if fn.endswith(".py"):
                py_files.append(os.path.join(root, fn))
    return py_files


files = collect_python_files("/content/clean-architecture")
print("Найдено .py-файлов:", len(files))


system_prompt = "Ты — эксперт по архитектуре программного обеспечения. Должен в ответ на присланный код присылать краткое описание того, как работает эта программа. Не вставляй никакой код в свой ответ. Только краткое текстовое описание работы"

headers = {
    "Authorization": f"Api-Key {API_KEY}",
    "x-folder-id": FOLDER_ID,
    "Content-Type": "application/json",
}


def generate_doc_for_file(filepath: str) -> str:
    code = Path(filepath).read_text(encoding="utf-8")
    if not code.strip():
        print(f"Skipping empty file: {filepath}")
        return ""

    payload = {
        "modelUri": model_uri,
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 1500},
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": code},
        ],
    }

    print(filepath)

    r = requests.post(URL, headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        print(f"Status code: {r.status_code}")
        print(f"Response content: {r.text}")
    r.raise_for_status()
    return r.json()["result"]["alternatives"][0]["message"]["text"]

def zip_docs() -> Path:
    """
    Creates a zip archive of the generated documentation
    Returns path to the created zip file
    """
    docs_path = Path("/content/generated_docs")
    zip_path = Path("/content/docs.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in docs_path.rglob("*"):
            if file.is_file():
                zipf.write(file, file.relative_to(docs_path))

    return zip_path


def generate_docs(zip_file: bytes) -> Path:
    """
    Generates documentation for the provided zip file
    Returns path to generated zip file
    """
    # Create paths using Path objects
    # Setup paths
    temp_dir = Path("/content/temp_repo")
    output_dir = Path("/content/generated_docs")
    

    # Create directories
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean up existing content
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    # Unzip the received bytes
    unzip_bytes_to_dir(zip_file, str(temp_dir))

    # Collect Python files
    py_files = collect_python_files(str(temp_dir))
    print(f"Будем обрабатывать {len(py_files)} файлов…")

    for path in py_files:
        try:
            print("Обработка:", path)
            doc = generate_doc_for_file(path)
            md_name = Path(path).relative_to(temp_dir).with_suffix(".md")
            out_path = output_dir / md_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(doc, encoding="utf-8")
            print("Сохранено:", out_path)
        except Exception as e:
            print("Ошибка для", path, ":", e)


def generate_module_docs():

    docs_root = Path("/content/generated_docs")
    HEADERS = headers  # Reuse headers defined above

    MAX_CHARS = 10000  # ограничение размера запроса

    def merge_batch(mod_name: str, files_batch: list[tuple[str, str]]) -> str:
        joined = "\n\n".join(f"### {Path(path).name}\n{text}" for path, text in files_batch)
        prompt = (
            f"Документации файлов модуля `{mod_name}`. Слей их в единое описание. "
            f"Опиши архитектуру, назначение, компоненты и use-cases. Markdown-формат.\n\n{joined}"
        )
        payload = {
            "modelUri": MODEL_URI,
            "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 1200},
            "messages": [
                {
                    "role": "system",
                    "text": "Ты — AI-документовед. Объединяй документации файлов в описание модуля.",
                },
                {"role": "user", "text": prompt},
            ],
        }
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["result"]["alternatives"][0]["message"]["text"]

    def split_into_batches(md_files, max_chars=MAX_CHARS):
        batches, batch, size = [], [], 0
        for f in md_files:
            length = len(f[1])
            if size + length > max_chars and batch:
                batches.append(batch)
                batch, size = [], 0
            batch.append(f)
            size += length
        if batch:
            batches.append(batch)
        return batches

    # Основной цикл с батчами
    for mod_dir in docs_root.iterdir():
        if not mod_dir.is_dir():
            continue
        mod_name = mod_dir.name
        print(f"\n📦 Модуль: {mod_name}")

        md_files = [(str(f), f.read_text(encoding="utf-8")) for f in mod_dir.rglob("*.md")]
        if not md_files:
            print(f"Нет документов для модуля {mod_name}")
            continue

        batches = split_into_batches(md_files)
        print(f"Разбили на {len(batches)} батчей.")

        module_docs = []
        for i, batch in enumerate(batches, 1):
            print(f"🔸 Отправляем батч {i}/{len(batches)} (файлов: {len(batch)})")
            try:
                part_doc = merge_batch(mod_name, batch)
                module_docs.append(part_doc)
            except requests.exceptions.HTTPError as e:
                print(f"Ошибка на батче {i} модуля '{mod_name}': {e}")
                continue

        final_doc = "\n\n".join(module_docs)

        #  Теперь сохраняем внутри папки модуля:
        out_path = mod_dir / f"{mod_name}_module.md"
        out_path.write_text(final_doc, encoding="utf-8")
        print(f"Сохранено в папке модуля: {out_path}")


def generate_overview_docs():
    docs_root = Path("/content/generated_docs")
    output_path = docs_root / "project_overview.md"

    from urllib.parse import quote

    project_root_path = Path("/content")

    module_entries = []
    module_docs = []

    for f in docs_root.rglob("*_module.md"):
        mod_name = f.stem.replace("_module", "")
        rel_doc_path = f.relative_to(docs_root)

        source_mod_path = project_root_path / rel_doc_path.parent
        source_mod_path_str = str(source_mod_path).replace("\\", "/")

        md_link = f"[{mod_name}]({quote(source_mod_path_str)})"

        module_entries.append(f"- {md_link}  \n  📁 Путь: `{source_mod_path_str}`")

        text = f.read_text(encoding="utf-8")
        module_docs.append((mod_name, text))

    module_summary_md = "### Основные компоненты и модули\n\n" + "\n".join(module_entries)

    joined = "\n\n".join(f"## {mod_name}\n\n{text[:2000]}" for mod_name, text in module_docs)

    prompt = (
        "Создай краткое и структурированное описание проекта на основе документации его модулей. "
        "Включи следующие разделы:\n"
        "- Назначение системы\n"
        "- Архитектурный стиль и принципы\n"
        "- Основные компоненты и модули (с названиями, ссылками и путями)\n"
        "- Взаимодействие и ключевые сценарии (use-cases)\n\n"
        "Ответ — в Markdown.\n\n"
        f"{module_summary_md}\n\n"
        f"{joined}"
    )

    payload = {
        "modelUri": MODEL_URI,
        "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 2000},
        "messages": [
            {"role": "system", "text": "Ты — AI-архитектор. Составь краткое описание проекта на основе модульной документации."},
            {"role": "user", "text": prompt}
        ]
    }
    HEADERS = headers

    response = requests.post(URL, headers=HEADERS, json=payload, timeout=120)
    response.raise_for_status()
    overview = response.json()["result"]["alternatives"][0]["message"]["text"]

    output_path.write_text(overview, encoding="utf-8")
    print(f"✅ Сохранено: {output_path}")
    print("\n---\n", overview[:1000], "\n...")
