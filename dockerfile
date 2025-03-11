# Используем Python-образ
FROM python:3.10-slim


# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*



WORKDIR /app
# Устанавливаем зависимости

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . /app

# Запуск
#CMD ["python", "trilium-bot.py"]
