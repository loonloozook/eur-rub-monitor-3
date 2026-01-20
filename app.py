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
st.set_page_config(page_title="Анализ EUR/RUB", layout="centered")

# === ЗАГОЛОВКИ ===
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

# === ЛОГИКА ===

def get_cbr_rates() -> dict:
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
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(25)

        driver.get("https://www.profinance.ru/currency_eur.asp")
        time.sleep(3)
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

# === ФУНКЦИЯ ОБНОВЛЕНИЯ (CALLBACK) ===
def update_data():
    """Эта функция запускается ДО перезагрузки страницы"""
    
    # Чтобы пользователь видел, что что-то происходит (но в консоли логов)
    print("Начало обновления...") 
    
    cbr = get_cbr_rates()
    cny_moex = get_moex_cny()
    eur_cny = get_eur_cny_cross()
    market_rate = get_profinance_selenium()
    
    cross_rate = None
    if cny_moex and eur_cny:
        cross_rate = cny_moex * eur_cny
    
    # Записываем в память
    st.session_state['data'] = {
        'cbr': cbr,
        'cny_moex': cny_moex,
        'eur_cny': eur_cny,
        'market_rate': market_rate,
        'cross_rate': cross_rate,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# === ИНТЕРФЕЙС ===

st.title("💶 EUR/RUB Аналитика")

# Инициализация при первом входе
if 'data' not in st.session_state:
    with st.spinner("Первичная загрузка данных..."):
        update_data()

# КНОПКА С CALLBACK (Главное изменение)
# on_click гарантирует выполнение функции ДО отрисовки интерфейса
st.button("🔄 Обновить сейчас", type="primary", on_click=update_data)

# === ОТРИСОВКА ДАННЫХ ===
data = st.session_state['data']
cbr = data['cbr']
market_rate = data['market_rate']
cross_rate = data['cross_rate']
timestamp = data['timestamp']

st.write(f"**Дата обновления:** {timestamp}")
st.write(f"**Режим:** Selenium + API")

st.divider()

# 1. Курсы ЦБ
st.subheader(f"📊 Курсы ЦБ РФ (на {cbr.get('date', '...')})")
if cbr:
    col1, col2, col3 = st.columns(3)
    diff = cbr.get('EUR', 0) - cbr.get('EUR_prev', 0)
    col1.metric("EUR/RUB", f"{cbr.get('EUR', 0):.4f}", f"{diff:+.4f}")
    col2.metric("CNY/RUB", f"{cbr.get('CNY', 0):.4f}")
    col3.metric("USD/RUB", f"{cbr.get('USD', 0):.4f}")

# 2. Рынок
st.subheader("📈 Рыночные котировки EUR/RUB")
col_m1, col_m2 = st.columns(2)

with col_m1:
    if market_rate:
        st.metric("Profinance (Selenium)", f"{market_rate:.4f} ₽")
    else:
        st.metric("Profinance", "Н/Д")

with col_m2:
    if cross_rate:
        st.metric("Кросс-курс (Расчетный)", f"{cross_rate:.4f} ₽")
        st.caption(f"CNY (Moex): {data['cny_moex']} × EUR/CNY: {data['eur_cny']}")
    else:
        st.metric("Кросс-курс", "Н/Д")

# 3. Анализ и Прогноз
st.divider()

st.subheader("📉 Анализ")

main_rate = market_rate if market_rate else (cross_rate - 1.5 if cross_rate else None)
source_name = "Profinance" if market_rate else "Кросс-курс (скорр.)"

if main_rate and cbr.get('EUR'):
    diff_market = main_rate - cbr['EUR']
    st.write(f"💱 **Рынок vs ЦБ:** {main_rate:.4f} vs {cbr['EUR']:.4f} (**{diff_market:+.4f}**)")
    
    low, high = estimate_tomorrow_rate(main_rate, cbr['EUR'])
    
    st.info(f"📌 **ПРОГНОЗ курса ЦБ на завтра:** {low:.2f} – {high:.2f} ₽/€\n\n(источник: {source_name})")
    
elif main_rate:
    st.warning(f"Рыночный курс: {main_rate:.4f}. Нет данных ЦБ для сравнения.")
else:
    st.error("Данные недоступны. Попробуйте обновить еще раз.")
