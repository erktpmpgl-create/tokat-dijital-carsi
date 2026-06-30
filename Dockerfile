FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends nginx supervisor && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy python-jose passlib python-multipart httpx

COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

WORKDIR /app/backend
EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
