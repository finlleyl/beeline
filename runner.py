import argparse
from pathlib import Path

from dispatcher import dispatch_file


def is_hidden(path: Path, root: Path) -> bool:
    """
    Проверяет, содержит ли путь скрытые директории или файлы (начинающиеся с ".").
    Относительный путь до root проверяется на наличие сегментов, начинающихся с точки.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        # если не получается от root, проверяем весь path
        parts = path.parts
    else:
        parts = rel.parts
    return any(part.startswith('.') for part in parts)


def main():
    parser = argparse.ArgumentParser(
        description="Обходит все Python-файлы в указанном корне и вызывает dispatcher для каждого"
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Корневая директория для обхода (по умолчанию текущая)"
    )
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    if not root_path.is_dir():
        parser.error(f"Указанный путь '{args.root}' не является директорией")

    for py_file in root_path.rglob("*.py"):
        # игнорируем скрытые файлы/папки и сам runner
        if is_hidden(py_file, root_path) or py_file.name == Path(__file__).name:
            continue
        dispatch_file(py_file)


if __name__ == "__main__":
    main()
