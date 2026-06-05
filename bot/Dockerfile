FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiogram aiohttp

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]