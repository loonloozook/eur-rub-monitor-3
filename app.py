import streamlit as st
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

st.set_page_config(page_title="Timeweb Monitor", layout="centered")

def get_rate():
    try:
        # Настройки Chrome для работы в Docker
        options = Options()
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox") # Обязательно для Docker
        options.add_argument("--disable-dev-shm-usage") # Обязательно для Docker
        options.add_argument("--disable-gpu")
        
        # Автоматическая установка драйвера
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.set_page_load_timeout(30)
        
        # Заходим на сайт
        driver.get("https://www.profinance.ru/currency_eur.asp")
        time.sleep(5) # Чуть больше времени для облака
        html = driver.page_source
        driver.quit()

        # Поиск данных
        patterns = [
            r'EUR/RUB[^\d]*(\d{2}[.,]\d{2,4})',
            r'EURRUB[^\d]*(\d{2}[.,]\d{2,4})',
            r'bid["\s:=]+(\d{2}[.,]\d{2,4})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                val = float(match.replace(',', '.'))
                if 80 < val < 150:
                    return val
        return None

    except Exception as e:
        st.error(f"Ошибка системы: {e}")
        return None

# === ИНТЕРФЕЙС ===
st.title("☁️ Timeweb: Profinance Spy")

if st.button("🔎 Проверить курс", type="primary"):
    with st.spinner("Загружаю браузер в контейнере..."):
        rate = get_rate()
        if rate:
            st.success(f"Текущий курс: {rate} ₽")
        else:
            st.warning("Курс не найден на странице")