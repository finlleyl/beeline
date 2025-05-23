# Исследовательский Документ: Статический Анализ Кода с Использованием Joern и Neo4j

## 1. Введение

В этом исследовательском документе подробно описаны процессы изучения, эксперименты, проблемы и итоговые решения, связанные с созданием автоматизированной системы извлечения и визуализации архитектуры программного обеспечения из устаревших кодовых баз с помощью инструментов Joern, Neo4j и нейросетей для генерации UML-диаграмм.

---

## 2. Постановка задачи

Целью было создание масштабируемого SaaS-решения, способного анализировать крупные, сложные устаревшие репозитории (более 10 млн строк) на таких языках программирования, как Python, C, C++, COBOL, Visual Basic, Pascal, Perl и Fortran. Решение должно:

* Извлекать структурные данные (классы, методы, вызовы)
* Хранить и визуализировать архитектуру (UML-диаграммы)
* Предоставлять контекст нейросети для генерации документации и диаграмм

---

## 3. Начальное исследование

### 3.1 Изученные инструменты

* **Joern:** Мощный инструмент, способный генерировать графы свойств кода (CPG).
* **Fraunhofer-AISEC CPG:** Альтернативная библиотека.
* **GraphRAG и Codeviz:** Дополнительные инструменты, рассмотренные для улучшения контекста и визуализации.

### 3.2 Выбранный стек технологий

* Joern (извлечение CPG)
* Neo4j (графовая база данных)
* FastAPI (API-слой)
* Python (слой интеграции)

---

## 4. Подход к реализации

### 4.1 Архитектура решения

1. Пользователь загружает репозиторий или предоставляет URL GitHub.
2. Бэкенд FastAPI скачивает и распаковывает репозиторий.
3. Joern генерирует граф свойств кода (CPG).
4. Извлеченные данные сохраняются в Neo4j.
5. Графовые запросы извлекают данные для генерации промтов.
6. Нейросеть генерирует UML-диаграммы и документацию.

### 4.2 Столкнувшиеся проблемы

* **Проблемы установки и запуска Joern:**

  * Проблемы с доступом к демону Docker и запуском контейнера.
  * Ошибки конфигурации выделения памяти JVM (`-Xmx4G`).
  * Экспорт большого количества ненужных узлов (`LITERAL`, `BLOCK`, `MODIFIER` и т.д.) по умолчанию.

* **Несоответствия схемы Neo4j:**

  * Первоначальные запросы не работали из-за неправильных меток (`METHOD`, `IN_FILE`, `BELONGS_TO`) и отсутствующих свойств (`fullName`, `path`).

---

## 5. Интеграция Joern

### 5.1 Правильная конфигурация экспорта

Исправлено с помощью корректной опции экспорта:

```bash
joern-export --repr CPG14 --format neo4jcsv --out ./export-dir /path/to/cpg.bin
```

### 5.2 Стратегия очистки

Удаление ненужных узлов для оптимизации запросов Neo4j:

```cypher
MATCH (n)
WHERE NONE(l IN labels(n) WHERE l IN ["METHOD","TYPE_DECL","FILE","CALL"])
DETACH DELETE n;
```

---

## 6. Извлечение данных из Neo4j

После исправления меток и связей окончательные запросы стали такими:

```cypher
MATCH (m:METHOD)
RETURN id(m) AS id, m.name AS name, m.fullName AS fullName

MATCH (c:TYPE_DECL)
RETURN id(c) AS id, c.name AS name, c.fullName AS fullName

MATCH (f:FILE)
RETURN id(f) AS id, f.name AS name, f.path AS path

MATCH (a:METHOD)-[:CALLS]->(b:METHOD)
RETURN id(a) AS from, id(b) AS to
```

---

## 7. Интеграция с Python

Разработан скрипт на Python для извлечения данных из Neo4j и подготовки промтов для нейросети:

```python
import json
from neo4j import GraphDatabase

class Neo4jHelper:
    def __init__(self, uri, user, pwd):
        self.driver = GraphDatabase.driver(uri, auth=(user, pwd))

    def close(self):
        self.driver.close()

    def run(self, cypher):
        with self.driver.session() as session:
            return [record.data() for record in session.run(cypher)]

helper = Neo4jHelper("bolt://localhost:7687", "neo4j", "pass")
functions = helper.run("MATCH (m:METHOD) RETURN m.name AS name, m.fullName AS fullName")
classes = helper.run("MATCH (c:TYPE_DECL) RETURN c.name AS name, c.fullName AS fullName")
calls = helper.run("MATCH (src:METHOD)-[:CALLS]->(dst:METHOD) RETURN src.name AS caller, dst.name AS callee")

graph = {"functions": functions, "classes": classes, "calls": calls}
prompt = json.dumps(graph, indent=2)

helper.close()
```

---

## 8. Интеграция с нейросетями

Сформирован точный промт для генерации PlantUML-диаграмм:

```
Вы эксперт в области архитектуры программного обеспечения.
Вот JSON, описывающий архитектуру проекта:
{JSON}
Сгенерируйте PlantUML диаграммы с:
- Классами и методами
- Ассоциациями, показывающими вызовы
Предоставьте только корректный PlantUML код от @startuml до @enduml.
```

---

## 9. Итоговый пайплайн

1. Пользователь предоставляет исходный код.
2. Joern извлекает CPG.
3. Данные загружаются в Neo4j и очищаются.
4. Данные извлекаются из Neo4j в формате JSON.
5. JSON отправляется как промт в нейросеть.
6. Нейросеть генерирует UML-диаграммы и документацию.

---

## 10. Дальнейшие улучшения

* Автоматизировать очистку после экспорта Joern.
* Интегрировать исторические данные git для обогащения контекста.
* Расширить промты нейросети для повышения точности.
* Оптимизировать запросы Neo4j для работы с большими репозиториями.

---

## Заключение

На бумаге все звучит очень круто, но это выполняется долго. Построение графа на neo4j очень затрано от этого куча проблем)
Отказ от этого решения полное на время пока не найдется что то лучше 