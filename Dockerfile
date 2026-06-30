FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy python-jose passlib python-multipart httpx
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
WORKDIR /app/backend
EXPOSE 80
CMD uvicorn main:app --host 0.0.0.0 --port 80
