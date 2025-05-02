import os

def save_visible_files_with_content(root_dir=".", output_file="output.txt"):
    with open(output_file, "w", encoding="utf-8") as out:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Удаляем скрытые папки из обхода
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            
            for filename in filenames:
                if filename.startswith('.'):
                    continue  # Пропускаем скрытые файлы
                
                file_path = os.path.join(dirpath, filename)
                out.write(f"\n=== Путь к файлу: {file_path} ===\n")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        out.write(content + "\n")
                except Exception as e:
                    out.write(f"[ОШИБКА] Не удалось прочитать файл: {e}\n")

# Запуск
save_visible_files_with_content(".", "output.txt")
