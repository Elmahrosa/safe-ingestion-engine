.PHONY: run worker test lint

run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A infrastructure.queue.celery_app worker --loglevel=INFO

test:
	pytest -q

lint:
	python -m compileall api core collectors security services infrastructure tests
