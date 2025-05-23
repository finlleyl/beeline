

# Автоматизированный генератор документации и диаграмм

## Введение



1. **Генерация документации** на уровне файлов и модулей с помощью LLM (YandexGPT).
    
2. **Агрегация** документации файлов в документацию модуля, сохраняя структуру исходного репозитория.
    
3. **Создание общего обзора** проекта на основе модульных документаций.
    
    
4. **Генерация UML-диаграмм** (component и class) с фильтрацией непривязанных узлов.
    

## Структура 

1. **Подключение и настройка LLM**
    
    - Загрузка токенов, формирование системного и пользовательского prompt.
        
    - Функции для обращения к API (YandexGPT) и генерации документации файлов.
        
2. **Сбор документаций файлов**
    
    - Рекурсивный обход директории `generated_docs`
        
    - Чтение всех `.md` файлов для последующей агрегации.
        
3. **Двухэтапный пайплайн агрегации**
    
    - **Шаг 1:** LLM получает `tree` структуры и выделяет список логических модулей.
        
    - **Шаг 2:** Для каждого модуля рекурсивно собирается документация файлов и объединяется в один `.md` в папке модуля.
        
4. **Генерация общего обзора проекта**
    
    - Сбор всех `*_module.md`
        
    - Формирование prompt с разделами: цель проекта, архитектурный стиль, модули с ссылками, use-cases.
        
    - Сохранение `project_overview.md` в корне документаций.
        
5. **Анализ зависимостей**
    
    - **Статический анализ:**
        
        - Использование `pydeps` + Graphviz для визуализации зависимостей.
            
        - Скрипт на `ast` для программного построения dependency-graph.
            
    - **Анализ коммитов:**
        
        - Git лог для выявления файлов, часто изменяемых вместе (`Coupling by Commits`).
            
6. **Генерация UML-диаграмм**
    
    - **Component diagrams:**
        
        - `py2puml` для верхнеуровневых диаграмм пакетов.
            
    - **Class diagrams:**
        
        - `pyreverse` из Pylint для каждого Python-пакета.
            
        - Пост-обработка `.dot`: удаление узлов без связей (`->`).
            
        - Рендеринг отфильтрованного `.dot` в `PNG` с сохранением как `<module>_diagram.png` рядом с документацией.
            

## Ключевые решения и алгоритмы

- **Нормализация имён модулей:** CamelCase → snake_case для точного поиска в файловой структуре.
    
- **Пакетный обход:** комбинация `iterdir()` для модулей верхнего уровня и `rglob()` для рекурсивного поиска файлов.
    
- **Разбиение на батчи** (`split_into_batches`) для ограничения размера одного prompt API (до ~14 000 символов).
    
- **Фильтрация графов:** на основе анализа `.dot`-файлов сохраняются только узлы, участвующие в прямых связях.
    

## Результаты

- **Документация файлов**: Markdown-документы в `generated_docs/module/.../*.md`.
    
- **Документация модулей**: `module_docs/<module>.md` и внутри `generated_docs/...` дополнительных `*_module.md`.
    
- **Общий обзор**: `generated_docs/project_overview.md`.
    
- **Диаграммы зависимостей**: `deps.svg` (graphviz) и интерактивные графы через `pydeps`.
    
- **Component UML**: `diagrams/components/<module>_comp.svg`.
    
- **Class UML**: `generated_docs/.../<module>/<module>_diagram.png` с фильтрацией.
    

## Выводы и рекомендации

1. **Модульность**: предложенный двухэтапный подход устраняет шум от архитектурных слоёв (`use_cases`, `entities`).
    
2. **Гибридный анализ** зависимостей (AST + Git) покрывает и статический, и исторический случаи.
    
3. **UML-генерация**: комбинирование `py2puml` и `pyreverse` с фильтрацией узлов обеспечивает информативность диаграмм.
    
4. **Автоматизация**: весь процесс запускается из одной Colab-ячейки, интеграция в CI/CD возможна через аналогичные скрипты.
