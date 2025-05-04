import streamlit as st
import requests
from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle

st.set_page_config(page_title="CoSE-раскладка графа", layout="wide")
st.title("📊 Демонстрация CoSE-раскладки Cytoscape.js")

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

# Визуализация
st_link_analysis(
    example_elements,
    layout=cose_layout,
    node_styles=node_styles,
    edge_styles=edge_styles,
)
