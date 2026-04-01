FROM python:3.11-slim

WORKDIR /app

COPY backend /app/backend
COPY data /app/data

WORKDIR /app/backend

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]