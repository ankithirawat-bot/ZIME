from fastapi import FastAPI
from backend.app.routers import companies

from backend.app.database.database import engine
from backend.models.company import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ZIME",
    version="0.1.0",
    description="Evidence-driven investment research platform"
)
app.include_router(companies.router)

@app.get("/")
def home():
    return {
        "message": "Welcome to ZIME!",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }