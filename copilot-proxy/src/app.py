"""
Copilot Proxy - FastAPI application factory

A proxy server that exposes GitHub Copilot as an OpenAI-compatible API
with MCP (Model Context Protocol) tools support.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.routes import router
from src.mcp_client import clear_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    logger.info("🚀 Starting Copilot Proxy...")
    yield
    logger.info("👋 Shutting down Copilot Proxy...")
    clear_cache()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    application = FastAPI(
        title="Copilot Proxy",
        description="GitHub Copilot proxy with MCP tools support",
        version="1.0.0",
        lifespan=lifespan
    )
    application.include_router(router)
    return application


app = create_app()
