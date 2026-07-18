from fastapi import FastAPI

app = FastAPI(
    title="ZIME",
    version="0.1.0",
    description="Evidence-driven investment research platform"
)

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