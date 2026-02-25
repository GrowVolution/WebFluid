import os


class DefaultConfig:
    API_CONFIG = {
        "title": "WebFluid API",
        "version": "1.0.0",
        "root_path": "/api/v1",
    }

    PROXY_FIX = False

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = f"{os.getenv('REDIS_URL', 'redis://localhost:6379')}/1"
    RATELIMIT_DEFAULT = ["500/day", "100/hour"]
