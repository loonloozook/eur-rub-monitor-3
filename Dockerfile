# 1. Берем базовый Python
FROM python:3.9-slim

# 2. Устанавливаем системные утилиты и Google Chrome
RUN apt-get update && apt-get install -y wget gnupg unzip curl && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    apt-get clean

# 3. Настраиваем рабочую папку
WORKDIR /app

# 4. Копируем файлы
COPY . .

# 5. Устанавливаем библиотеки Python
RUN pip install -r requirements.txt

# 6. Команда запуска (порт 80 для Timeweb важен)
EXPOSE 80
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]