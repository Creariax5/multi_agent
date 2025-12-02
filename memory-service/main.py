"""
Memory Service - Stores user configs, linked accounts, and memories for RAG.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import models
from routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await models.init_db()
    yield

app = FastAPI(
    title="Memory Service",
    description="User configuration and memory storage for RAG",
    lifespan=lifespan
)

app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "memory-service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
