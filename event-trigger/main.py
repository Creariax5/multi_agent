"""
Event Trigger Service

Receives webhooks from various sources (email, Stripe, Slack, etc.)
and triggers AI processing with source-specific instructions.

Endpoints:
- POST /webhook/{source} - Receive webhook from any source
- POST /webhook/email - Receive email notifications
- POST /webhook/stripe - Receive Stripe webhooks
- POST /webhook/slack - Receive Slack events
- POST /webhook/zapier - Receive Zapier webhooks
- POST /trigger - Manual trigger with custom source
- GET /history - View recent processed events
- GET /instructions/{source} - View instructions for a source
"""
import json
import logging
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Any, Dict

from config import ENABLED_SOURCES, WEBHOOK_SECRET
from instructions import INSTRUCTIONS, get_instructions
from event_processor import event_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Event Trigger Service",
    description="Webhook receiver that triggers AI processing"
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

def validate_source(source: str) -> bool:
    """Check if source is enabled"""
    return source.lower() in [s.strip().lower() for s in ENABLED_SOURCES]


def validate_webhook_secret(request: Request) -> bool:
    """Validate webhook secret if configured"""
    if not WEBHOOK_SECRET:
        return True
    
    # Check various header locations for secret
    secret = (
        request.headers.get("X-Webhook-Secret") or
        request.headers.get("Authorization", "").replace("Bearer ", "") or
        request.query_params.get("secret")
    )
    return secret == WEBHOOK_SECRET


# ============================================================================
# Routes
# ============================================================================

@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "event-trigger",
        "status": "running",
        "enabled_sources": ENABLED_SOURCES,
        "available_sources": list(INSTRUCTIONS.keys())
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.get("/instructions")
async def list_instructions():
    """List all available instruction templates"""
    return {
        source: instructions[:200] + "..." 
        for source, instructions in INSTRUCTIONS.items()
    }


@app.get("/instructions/{source}")
async def get_source_instructions(source: str):
    """Get instructions for a specific source"""
    instructions = get_instructions(source)
    return {
        "source": source,
        "instructions": instructions
    }


@app.get("/history")
async def get_history(limit: int = 20):
    """Get recent event processing history"""
    return {
        "events": event_processor.get_history(limit),
        "total": len(event_processor.history)
    }


# ============================================================================
# Webhook Endpoints
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
    Generic webhook handler for any source.
    
    The source determines which instructions template to use.
    """
    # Validate
    if not validate_source(source):
        raise HTTPException(400, f"Source '{source}' not enabled")
    
    if not validate_webhook_secret(request):
        raise HTTPException(401, "Invalid webhook secret")
    
    # Parse body
    try:
        body = await request.json()
    except:
        body = dict(await request.form()) or {"raw": (await request.body()).decode()}
    
    logger.info(f"📥 Received {source} webhook")
    
    # Process
    if stream:
        return StreamingResponse(
            event_processor.process_streaming(source, body, instructions, model),
            media_type="text/event-stream"
        )
    else:
        # Process in background for faster webhook response
        background_tasks.add_task(
            event_processor.process,
            source, body, instructions, model
        )
        
        return WebhookResponse(
            success=True,
            message=f"Event queued for processing",
            event_id=len(event_processor.history) + 1
        )


@app.post("/webhook/email")
async def email_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Email webhook endpoint.
    
    Expected payload:
    {
        "from": "sender@example.com",
        "to": "recipient@example.com", 
        "subject": "Email subject",
        "body": "Email content",
        "date": "2024-01-01T12:00:00Z",
        "attachments": ["file1.pdf"]
    }
    """
    body = await request.json()
    logger.info(f"📧 Email from: {body.get('from', 'unknown')}")
    
    background_tasks.add_task(event_processor.process, "email", body)
    
    return WebhookResponse(success=True, message="Email queued for processing")


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Stripe webhook endpoint.
    
    Receives standard Stripe webhook payloads.
    Configure in Stripe Dashboard: https://dashboard.stripe.com/webhooks
    """
    body = await request.json()
    event_type = body.get("type", "unknown")
    logger.info(f"💳 Stripe event: {event_type}")
    
    background_tasks.add_task(event_processor.process, "stripe", body)
    
    return WebhookResponse(success=True, message=f"Stripe {event_type} queued")


@app.post("/webhook/slack")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Slack webhook endpoint.
    
    Handles Slack Events API payloads.
    Configure in Slack App settings: https://api.slack.com/apps
    """
    body = await request.json()
    
    # Handle Slack URL verification challenge
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}
    
    event = body.get("event", body)
    logger.info(f"💬 Slack message from: {event.get('user', 'unknown')}")
    
    background_tasks.add_task(event_processor.process, "slack", event)
    
    return WebhookResponse(success=True, message="Slack event queued")


@app.post("/webhook/zapier")
async def zapier_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Zapier webhook endpoint.
    
    Receives webhooks from Zapier "Webhooks by Zapier" action.
    Create a Zap with "Webhooks by Zapier" -> POST to this endpoint.
    """
    body = await request.json()
    source_hint = body.get("_source", body.get("source", "zapier"))
    logger.info(f"⚡ Zapier webhook: {source_hint}")
    
    # If Zapier provides a source hint, use that for instructions
    actual_source = source_hint if source_hint in INSTRUCTIONS else "zapier"
    
    background_tasks.add_task(event_processor.process, actual_source, body)
    
    return WebhookResponse(success=True, message="Zapier event queued")


@app.post("/webhook/calendar")
async def calendar_webhook(request: Request, background_tasks: BackgroundTasks):
    """Calendar event webhook"""
    body = await request.json()
    logger.info(f"📅 Calendar event: {body.get('summary', 'unknown')}")
    
    background_tasks.add_task(event_processor.process, "calendar", body)
    
    return WebhookResponse(success=True, message="Calendar event queued")


@app.post("/webhook/form")
async def form_webhook(request: Request, background_tasks: BackgroundTasks):
    """Form submission webhook"""
    try:
        body = await request.json()
    except:
        body = dict(await request.form())
    
    logger.info(f"📝 Form submission received")
    
    background_tasks.add_task(event_processor.process, "form", body)
    
    return WebhookResponse(success=True, message="Form submission queued")


# ============================================================================
# Manual Trigger
# ============================================================================

@app.post("/trigger")
async def manual_trigger(req: TriggerRequest):
    """
    Manual trigger endpoint for testing or custom integrations.
    
    Allows specifying custom instructions and streaming.
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
        result = await event_processor.process(
            req.source, req.data, req.instructions, req.model
        )
        return result


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
