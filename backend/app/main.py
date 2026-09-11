import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.limiter import limiter

settings = get_settings()

if settings.environment == "production" and settings.secret_key == "change-me-to-a-long-random-string":
    raise RuntimeError(
        "SECRET_KEY is still the default placeholder. Set a unique, random SECRET_KEY "
        "before running with ENVIRONMENT=production — it signs every access/refresh/"
        "password-reset token."
    )

app = FastAPI(title="Acadex API", version="0.1.0")

if settings.storage_backend == "local":
    os.makedirs(settings.storage_local_path, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.storage_local_path), name="uploads")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition isn't on the CORS-safelisted response header list,
    # so without this, JS can read a download's bytes but never its
    # filename (see app.lib.api-client.downloadFile, Phase 10 export).
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {"name": "Acadex API", "status": "running"}
