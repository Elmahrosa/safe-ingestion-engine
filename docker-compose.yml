services:
  api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    env_file:
      - .env
    volumes:
      - ./:/app
      - ./data:/app/data
    ports:
      - "8000:8000"
    depends_on:
      - redis

  worker:
    build: .
    command: celery -A infrastructure.queue.celery_app worker --loglevel=INFO
    env_file:
      - .env
    volumes:
      - ./:/app
      - ./data:/app/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
