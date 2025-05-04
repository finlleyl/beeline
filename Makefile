uvicorn:
			uvicorn visualization.backend.main:app --reload


streamlit:
			streamlit run visualization/frontend/main.py
