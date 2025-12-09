from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
import os

app = FastAPI(title="AI Trivia")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080")


async def call_ai(prompt: str) -> dict:
    """Call the AI and parse JSON response"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{COPILOT_PROXY_URL}/v1/chat/completions",
            json={
                "model": "gpt-4.1",
                "messages": [
                    {"role": "system", "content": "Tu es un générateur de quiz. Retourne UNIQUEMENT du JSON valide, sans markdown."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "use_tools": False
            }
        )
        
        if response.status_code != 200:
            return {"error": f"API Error: {response.status_code}"}
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        # Parse JSON from response
        try:
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # Find JSON object
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                return json.loads(content[start:end+1])
            return json.loads(content.strip())
        except Exception as e:
            return {"error": f"Parse error: {str(e)}", "raw": content}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/question")
async def generate_question(request: Request):
    """Generate a new trivia question"""
    body = await request.json()
    category = body.get("category", "culture générale")
    difficulty = body.get("difficulty", 3)
    recent_topics = body.get("recent_topics", [])

    avoid_text = f"\nÉvite ces sujets déjà utilisés: {', '.join(recent_topics[-5:])}" if recent_topics else ""

    prompt = f"""Génère une question de quiz intéressante sur: {category}
Difficulté: {difficulty}/5 (1=très facile, 5=expert){avoid_text}

Retourne un JSON avec:
{{
    "question": "la question (claire et précise)",
    "choices": ["choix A", "choix B", "choix C", "choix D"],
    "correct": 0,
    "explanation": "explication de la bonne réponse + un fun fact",
    "topic": "le sujet spécifique"
}}

IMPORTANT: correct est l'INDEX (0, 1, 2 ou 3) de la bonne réponse dans choices."""

    result = await call_ai(prompt)
    
    if "error" not in result:
        result["correct"] = int(result.get("correct", 0))
        # Validate choices exist
        if "choices" not in result or len(result.get("choices", [])) != 4:
            result = {"error": "Invalid response format", "raw": str(result)}
    
    return JSONResponse(result)


@app.post("/api/custom-question")
async def custom_question(request: Request):
    """Generate a question on a custom theme"""
    body = await request.json()
    theme = body.get("theme", "")
    difficulty = body.get("difficulty", 3)

    prompt = f"""Génère une question de quiz sur le thème: "{theme}"
Difficulté: {difficulty}/5

Retourne un JSON avec:
{{
    "question": "la question",
    "choices": ["choix A", "choix B", "choix C", "choix D"],
    "correct": 0,
    "explanation": "explication + fun fact",
    "topic": "sujet spécifique"
}}

IMPORTANT: correct est l'INDEX (0, 1, 2 ou 3) de la bonne réponse."""

    result = await call_ai(prompt)
    
    if "error" not in result:
        result["correct"] = int(result.get("correct", 0))
        if "choices" not in result or len(result.get("choices", [])) != 4:
            result = {"error": "Invalid response format", "raw": str(result)}
    
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3004)
