
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --retries 10 --timeout 120 --index-url https://pypi.org/simple -r /app/requirements.txt


COPY backend /app/backend
COPY data/knowledge_base/constitution_articles.json /app/data/knowledge_base/constitution_articles.json

WORKDIR /app/backend

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
