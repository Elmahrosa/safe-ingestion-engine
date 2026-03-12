install:
	pip install -r requirements.txt

dev:
	uvicorn api.server:app --reload

test:
	pytest

lint:
	ruff .

docker:
	docker compose up

openapi:
	curl http://localhost:8000/openapi.json -o docs/openapi.json
