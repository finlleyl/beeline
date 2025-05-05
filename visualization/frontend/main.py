import streamlit as st
import requests
from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle
from pydantic import BaseModel
from typing import Optional

st.set_page_config(page_title="CoSE-раскладка графа", layout="wide")
st.title("📊 Демонстрация CoSE-раскладки Cytoscape.js")

# Модель для запроса анализа функции
class FunctionAnalysisRequest(BaseModel):
    file_path: str
    start_line: int
    end_line: int

# Функция для отправки запроса на анализ
def analyze_function(file_path: str, start_line: int, end_line: int) -> Optional[str]:
    try:
        response = requests.post(
            "http://localhost:8000/git-analysis/analyze-function",
            json={
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка при анализе функции: {str(e)}")
        return None

# Примерная структура
example_elements = {
    "nodes": [{"data": {"id": x, "label": f"Node {x}"}} for x in range(1, 7)],
    "edges": [
        {"data": {"source": u, "target": v, "label": f"{u}->{v}"}}
        for u in map(str, range(1, 7))
        for v in map(str, range(1, 7))
        if u != v
    ],
}

# Стили узлов
node_styles = [
    NodeStyle(f"Node {i}", color, "label")
    for i, color in enumerate(
        ["#FF7F3E", "#2A629A", "#20A39E", "#D81159", "#8F2D56", "#218380"], 1
    )
]

# Стили рёбер
edge_styles = [
    EdgeStyle(f"{u}->{v}", caption="label", directed=True)
    for u in map(str, range(1, 7))
    for v in map(str, range(1, 7))
    if u != v
]

# Параметры CoSE-Bilkent макета
cose_layout = {
    "name": "cose",  # или 'cose-bilkent'
    "idealEdgeLength": 100,
    "nodeRepulsion": 4500,
    "edgeElasticity": 0.45,
    "nestingFactor": 0.1,
    "gravity": 0.25,
    "numIter": 2500,
    "animate": True,
    "animationDuration": 1000,
    "randomize": False,
    "componentSpacing": 40,
}

# Добавляем контекстное меню для анализа функции
st.sidebar.title("Анализ функции")
selected_file = st.sidebar.text_input("Путь к файлу")
start_line = st.sidebar.number_input("Начальная строка", min_value=1, value=1)
end_line = st.sidebar.number_input("Конечная строка", min_value=1, value=1)

if st.sidebar.button("Проанализировать функцию"):
    if selected_file and start_line and end_line:
        result = analyze_function(selected_file, start_line, end_line)
        if result:
            st.sidebar.success("Анализ завершен")
            st.sidebar.json(result)
    else:
        st.sidebar.error("Пожалуйста, заполните все поля")

# Визуализация
st_link_analysis(
    example_elements,
    layout=cose_layout,
    node_styles=node_styles,
    edge_styles=edge_styles,
)
