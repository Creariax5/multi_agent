"""
Event Trigger Service

Receives webhooks from various sources and triggers AI processing.
Sources are auto-discovered from the sources/ directory.

Add a new source by creating a .py file in sources/ with:
  - get_definition() -> dict
  - get_instructions() -> str
  - format_event(data) -> str
"""
import logging
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict

from config import WEBHOOK_SECRET
from sources import registry
from event_processor import event_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Event Trigger Service",
    description="Webhook receiver that triggers AI processing - Sources are auto-discovered"
)


# ============================================================================
# Models
# ============================================================================

class TriggerRequest(BaseModel):
    source: str
    data: Dict[str, Any]
    instructions: Optional[str] = None
    model: Optional[str] = None
    stream: bool = False


class WebhookResponse(BaseModel):
    success: bool
    message: str
    event_id: Optional[int] = None


# ============================================================================
# Helpers
# ============================================================================

def validate_webhook_secret(request: Request) -> bool:
    """Validate webhook secret if configured"""
    if not WEBHOOK_SECRET:
        return True
    
    secret = (
        request.headers.get("X-Webhook-Secret") or
        request.headers.get("Authorization", "").replace("Bearer ", "") or
        request.query_params.get("secret")
    )
    return secret == WEBHOOK_SECRET


async def parse_body(request: Request) -> Dict[str, Any]:
    """Parse request body (JSON or form data)"""
    try:
        return await request.json()
    except:
        form = await request.form()
        if form:
            return dict(form)
        raw = await request.body()
        return {"raw": raw.decode()} if raw else {}


# ============================================================================
# Routes
# ============================================================================

@app.on_event("startup")
async def startup():
    """Load source plugins on startup"""
    registry.load_all()
    registry.register_routes(app)


@app.get("/")
async def root():
    """Service info with all discovered sources"""
    return {
        "service": "event-trigger",
        "status": "running",
        "sources": registry.list_sources(),
        "endpoints": {
            "webhook": "/webhook/{source}",
            "trigger": "/trigger",
            "trigger_sync": "/trigger/sync",
            "history": "/history",
            "sources": "/sources"
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "sources_loaded": len(registry.sources)
    }


@app.get("/sources")
async def list_sources():
    """List all available source plugins"""
    return {
        "sources": registry.list_sources(),
        "total": len(registry.sources)
    }


@app.get("/sources/{source}")
async def get_source_info(source: str):
    """Get details about a specific source"""
    definition = registry.get_definition(source)
    if not definition:
        raise HTTPException(404, f"Source '{source}' not found")
    
    return {
        "source": source,
        "definition": definition,
        "instructions": registry.get_instructions(source)[:500] + "..."
    }


@app.get("/history")
async def get_history(limit: int = 20):
    """Get recent event processing history"""
    return {
        "events": event_processor.get_history(limit),
        "total": len(event_processor.history)
    }


# ============================================================================
# Universal Webhook Handler
# ============================================================================

@app.post("/webhook/{source}")
async def webhook_handler(
    source: str,
    request: Request,
    background_tasks: BackgroundTasks,
    stream: bool = False,
    model: Optional[str] = None,
    instructions: Optional[str] = None
):
    """
    Universal webhook handler for any source.
    
    The source determines which plugin handles formatting and instructions.
    Unknown sources fall back to the 'generic' plugin.
    """
    if not validate_webhook_secret(request):
        raise HTTPException(401, "Invalid webhook secret")
    
    body = await parse_body(request)
    
    # Log raw body for debugging
    logger.info(f"📥 Received {source} webhook - Raw data: {body}")
    
    # Handle Slack challenge (special case)
    if source == "slack" and body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}
    
    # Use generic if source not found
    actual_source = source if registry.get_source(source) else "generic"
    
    logger.info(f"📥 Received {source} webhook")
    
    if stream:
        return StreamingResponse(
            event_processor.process_streaming(actual_source, body, instructions, model),
            media_type="text/event-stream"
        )
    else:
        background_tasks.add_task(
            event_processor.process,
            actual_source, body, instructions, model
        )
        
        return WebhookResponse(
            success=True,
            message=f"{source} event queued for processing",
            event_id=len(event_processor.history) + 1
        )


# ============================================================================
# Manual Triggers
# ============================================================================

@app.post("/trigger")
async def manual_trigger(req: TriggerRequest, background_tasks: BackgroundTasks):
    """
    Manual trigger endpoint for testing or custom integrations.
    Processes in background by default.
    """
    logger.info(f"🔧 Manual trigger: {req.source}")
    
    if req.stream:
        return StreamingResponse(
            event_processor.process_streaming(
                req.source, req.data, req.instructions, req.model
            ),
            media_type="text/event-stream"
        )
    else:
        background_tasks.add_task(
            event_processor.process,
            req.source, req.data, req.instructions, req.model
        )
        return WebhookResponse(
            success=True,
            message=f"{req.source} trigger queued",
            event_id=len(event_processor.history) + 1
        )


@app.post("/trigger/sync")
async def sync_trigger(req: TriggerRequest):
    """
    Synchronous trigger - waits for AI response.
    Useful for testing or when you need the response immediately.
    """
    logger.info(f"🔧 Sync trigger: {req.source}")
    
    result = await event_processor.process(
        req.source, req.data, req.instructions, req.model
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
