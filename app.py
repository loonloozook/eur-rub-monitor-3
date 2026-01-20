import streamlit as st
import time
import re
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple

# Библиотеки Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# === НАСТРОЙКИ СТРАНИЦЫ ===
st.set_page_config(page_title="Монитор EUR/RUB", layout="centered")

# === ЗАГОЛОВКИ И КОНСТАНТЫ ===
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

# === ЛОГИКА СБОРА ДАННЫХ ===

def get_cbr_rates() -> dict:
    """Официальные курсы ЦБ РФ"""
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        data = response.json()
        return {
            "EUR": data["Valute"]["EUR"]["Value"],
            "EUR_prev": data["Valute"]["EUR"]["Previous"],
            "CNY": data["Valute"]["CNY"]["Value"],
            "USD": data["Valute"]["USD"]["Value"],
            "date": data["Date"][:10]
        }
    except:
        return {}

def get_moex_cny() -> Optional[float]:
    """CNY/RUB с Мосбиржи"""
    url = "https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS/securities/CNYRUB_TOM.json"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        data = response.json()
        marketdata = data.get("marketdata", {}).get("data", [])
        cols = data.get("marketdata", {}).get("columns", [])
        if marketdata and "LAST" in cols:
            return float(marketdata[0][cols.index("LAST")])
    except:
        pass
    return None

def get_eur_cny_cross() -> Optional[float]:
    """EUR/CNY кросс-курс"""
    try:
        url = "https://api.frankfurter.app/latest?from=EUR&to=CNY"
        data = requests.get(url, timeout=5).json()
        return data["rates"]["CNY"]
    except:
        try:
            url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json"
            data = requests.get(url, timeout=5).json()
            return data["eur"]["cny"]
        except:
            return None

def get_profinance_selenium() -> Optional[float]:
    """Парсинг через скрытый браузер"""
    try:
        options = Options()
        # Настройки для Docker/Server
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)

        driver.get("https://www.profinance.ru/currency_eur.asp")
        time.sleep(3) # Ждем JS
        page_source = driver.page_source
        driver.quit()

        patterns = [
            r'EUR/RUB[^\d]*(\d{2}[.,]\d{2,4})',
            r'EURRUB[^\d]*(\d{2}[.,]\d{2,4})',
            r'bid["\s:=]+(\d{2}[.,]\d{2,4})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            for match in matches:
                val = float(match.replace(',', '.'))
                if 80 < val < 200:
                    return val
        return None
    except:
        return None

def estimate_tomorrow_rate(current_market: float, cbr_today: float) -> Tuple[float, float]:
    estimate = current_market * 0.6 + cbr_today * 0.4
    return estimate - 0.2, estimate + 0.2

# === ФУНКЦИЯ ОБНОВЛЕНИЯ СОСТОЯНИЯ ===

def update_data():
    """Эта функция запускает весь процесс и сохраняет результат в память"""
    with st.spinner('⏳ Идет загрузка данных (Selenium + API)...'):
        
        # 1. Загружаем всё
        cbr = get_cbr_rates()
        cny_moex = get_moex_cny()
        eur_cny = get_eur_cny_cross()
        market_rate = get_profinance_selenium()
        
        # 2. Считаем кросс
        cross_rate = None
        if cny_moex and eur_cny:
            cross_rate = cny_moex * eur_cny
        
        # 3. Сохраняем в память сессии (st.session_state)
        st.session_state['data'] = {
            'cbr': cbr,
            'cny_moex': cny_moex,
            'eur_cny': eur_cny,
            'market_rate': market_rate,
            'cross_rate': cross_rate,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# === ИНТЕРФЕЙС ===

st.title("💶 Мониторинг EUR/RUB")

# Кнопка обновления
if st.button("🔄 Обновить сейчас", type="primary"):
    update_data()

# Если данных еще нет (первый запуск), загружаем их автоматически
if 'data' not in st.session_state:
    update_data()

# === ОТОБРАЖЕНИЕ (Берем данные ТОЛЬКО из памяти) ===
data = st.session_state['data']
cbr = data['cbr']
market_rate = data['market_rate']
cross_rate = data['cross_rate']

st.caption(f"Последнее обновление: {data['timestamp']}")

st.divider()

# 1. Блок ЦБ
st.subheader(f"📊 Курсы ЦБ РФ (на {cbr.get('date', '...')})")
if cbr:
    col1, col2, col3 = st.columns(3)
    diff = cbr.get('EUR', 0) - cbr.get('EUR_prev', 0)
    col1.metric("EUR/RUB", f"{cbr.get('EUR', 0):.4f}", f"{diff:+.4f}")
    col2.metric("CNY/RUB", f"{cbr.get('CNY', 0):.4f}")
    col3.metric("USD/RUB", f"{cbr.get('USD', 0):.4f}")

# 2. Блок Рынок
st.subheader("📈 Рыночные котировки EUR/RUB")
col_m1, col_m2 = st.columns(2)

with col_m1:
    if market_rate:
        st.metric("Profinance (Selenium)", f"{market_rate:.4f} ₽")
    else:
        st.metric("Profinance", "Н/Д", delta_color="off")

with col_m2:
    if cross_rate:
        st.metric("Кросс-курс (через CNY)", f"{cross_rate:.4f} ₽")
        st.caption(f"MOEX CNY: {data['cny_moex']} × EUR/CNY: {data['eur_cny']}")
    else:
        st.metric("Кросс-курс", "Н/Д")

# 3. Блок Прогноз
st.divider()

# Выбор главного курса: Profinance или Кросс (если Profinance не работает)
main_rate = market_rate if market_rate else (cross_rate - 1.5 if cross_rate else None)
source_name = "Profinance" if market_rate else "Кросс-курс (скорр.)"

if main_rate and cbr.get('EUR'):
    diff_market = main_rate - cbr['EUR']
    st.write(f"💱 **Рынок vs ЦБ:** {main_rate:.4f} vs {cbr['EUR']:.4f} (**{diff_market:+.4f}**)")
    
    low, high = estimate_tomorrow_rate(main_rate, cbr['EUR'])
    
    # Красивая синяя плашка как requested
    st.info(f"📌 **ПРОГНОЗ курса ЦБ на завтра:** {low:.2f} – {high:.2f} ₽/€\n\n(источник: {source_name})")
    
elif main_rate:
    st.warning(f"Рыночный курс: {main_rate:.4f}. Данных ЦБ для сравнения нет.")
else:
    st.error("Данные недоступны. Нажмите «Обновить», возможно сайт Profinance временно не отвечает.")
