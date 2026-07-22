import logging

from fastapi import FastAPI

from backend.app.database.database import engine
from backend.app.routers import companies
from backend.core.api_constants import HEALTH_ENDPOINT
from backend.core.app_metadata import get_app_metadata
from backend.core.startup_validation import assert_startup_validations
from backend.models.company import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Startup validation — fail fast on missing dependencies ────────────
assert_startup_validations()

Base.metadata.create_all(bind=engine)

metadata = get_app_metadata()

app = FastAPI(
    title=metadata.api_title,
    version=metadata.version,
    description=metadata.description,
    docs_url=metadata.docs_url,
    redoc_url=metadata.redoc_url,
    openapi_url=metadata.openapi_url,
)
app.include_router(companies.router)


@app.get("/")
def home():
    return {
        "message": "Welcome to ZIME!",
        "status": "running"
    }


@app.get(HEALTH_ENDPOINT)
def health():
    return {
        "status": "healthy"
    }
