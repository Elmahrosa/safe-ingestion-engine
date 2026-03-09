"""
main.py — Entry point for local development.
Fix: load_dotenv() was called on every import, overriding env vars already
     set by Docker/docker-compose. Moved inside __main__ guard.
"""

import uvicorn


def main():
    from dotenv import load_dotenv
    load_dotenv()  # Only loads .env if vars not already set — safe in Docker

    from core.database import init_db
    init_db()

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
