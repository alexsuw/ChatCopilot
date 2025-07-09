FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for building some Python packages
RUN apt-get update && apt-get install -y build-essential pkg-config libffi-dev

# Copy requirements first for better caching
COPY requirements.txt .

# Force remove any cached appwrite and httpx versions and install fresh
RUN pip uninstall -y appwrite httpx || true
RUN pip cache purge
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

# Copy the application code
COPY . .

# Expose port
EXPOSE 8000

# Установка переменной окружения PYTHONPATH, чтобы Python находил папку src
ENV PYTHONPATH=/app

# Установка рабочей директории
WORKDIR /app

# Запуск приложения
CMD ["python", "main.py"] 