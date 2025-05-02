import streamlit as st
import requests
import time

# Параметры long polling
POLL_URL = "http://your-server.com/poll"
TIMEOUT = 60  # максимум ждать 60 секунд


# Функция long polling
def long_poll(url: str, timeout: int = 60):
    """
    Отсылает GET-запрос и ждёт до `timeout` секунд ответа от сервера.
    Если timeout истёк без ответа, повторяет запрос.
    Возвращает распаршенный JSON.
    """
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            # Как только получили ответ, возвращаем данные
            return response.json()
        except requests.exceptions.ReadTimeout:
            # Если соединение было закрыто по таймауту — повторяем
            continue
        except requests.exceptions.RequestException as e:
            st.error(f"Ошибка при long polling: {e}")
            time.sleep(5)
            continue


st.title("Пример long polling в Streamlit")

# Место для вывода новых данных
placeholder = st.empty()

if st.button("Старт polling"):
    st.info("Ждём новых данных...")
    # Запускаем нескончаемый цикл long polling
    while True:
        data = long_poll(POLL_URL, TIMEOUT)
        # Обновляем содержимое в placeholder
        placeholder.json(data)
        # Можно добавить звук или уведомление
        st.success("Появились новые данные!")
        # Не делаем задержку, сразу запрашиваем снова
