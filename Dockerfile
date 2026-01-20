# 1. Базовый образ Python
FROM python:3.9-slim

# 2. Устанавливаем wget (качалку) и сам Google Chrome напрямую через .deb файл
# Это позволяет избежать возни с GPG-ключами и apt-key
RUN apt-get update && apt-get install -y wget && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean

# 3. Рабочая папка
WORKDIR /app

# 4. Копируем файлы
COPY . .

# 5. Ставим библиотеки
RUN pip install -r requirements.txt

# 6. Запускаем
EXPOSE 80
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]
