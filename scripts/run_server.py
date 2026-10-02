"""Launch using APP_HOST and APP_PORT from environment/.env."""

import uvicorn

from app.config import Settings

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port)
