"""Copilot Proxy - FastAPI application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.routes import router
from src.mcp_client import clear_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Copilot Proxy...")
    yield
    logger.info("👋 Shutting down...")
    clear_cache()


app = FastAPI(title="Copilot Proxy", version="1.0.0", lifespan=lifespan)
app.include_router(router)
