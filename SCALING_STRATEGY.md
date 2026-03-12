# Operations

## Start stack
```bash
docker compose up --build
```

## Run tests
```bash
pytest -q
```

## Key checks
- `/health`
- `/docs`
- worker can connect to Redis
- `.env` contains valid secret values
