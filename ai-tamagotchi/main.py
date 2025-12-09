from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
import os

app = FastAPI(title="AI Tamagotchi")

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
                    {"role": "system", "content": "Tu es un générateur de Tamagotchi. Retourne UNIQUEMENT du JSON valide, sans markdown."},
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
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
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


@app.post("/api/generate")
async def generate_tamagotchi():
    """Generate a new Tamagotchi with AI"""
    prompt = """Génère un Tamagotchi unique et créatif avec:
{
    "name": "nom créatif",
    "species": "espèce réelle ou fantastique",
    "emoji": "un emoji représentatif",
    "personality": ["trait1", "trait2", "trait3"],
    "needs": {
        "nom_besoin_1": 80,
        "nom_besoin_2": 70,
        "nom_besoin_3": 60,
        "nom_besoin_4": 50
    },
    "intro": "phrase d'introduction du personnage",
    "level": 1,
    "xp": 0
}
Sois créatif avec les noms de besoins (pas juste faim/sommeil, invente selon la personnalité)."""

    result = await call_ai(prompt)
    return JSONResponse(result)


@app.post("/api/action")
async def do_action(request: Request):
    """Execute an action on the Tamagotchi"""
    body = await request.json()
    tamagotchi = body.get("tamagotchi", {})
    action = body.get("action", "parler")
    message = body.get("message", "")

    prompt = f"""Tu es {tamagotchi.get('name', 'Tama')}, un {tamagotchi.get('species', 'créature')}.
Ta personnalité : {', '.join(tamagotchi.get('personality', []))}.
Tes besoins actuels : {json.dumps(tamagotchi.get('needs', {}), ensure_ascii=False)}

L'utilisateur fait l'action : {action}
{f"Message : {message}" if message else ""}

Réponds en restant dans ton personnage (max 2 phrases).
Puis indique les nouveaux niveaux de besoins (entre 0 et 100).
Ajoute +5 à +15 XP selon l'interaction.

Retourne un JSON:
{{
    "response": "ta réponse en character",
    "needs": {{ ... les besoins mis à jour ... }},
    "xp_gained": 10
}}"""

    result = await call_ai(prompt)
    return JSONResponse(result)


@app.post("/api/event")
async def random_event(request: Request):
    """Generate a random event"""
    body = await request.json()
    tamagotchi = body.get("tamagotchi", {})

    prompt = f"""Tu es le narrateur pour {tamagotchi.get('name', 'Tama')}, un {tamagotchi.get('species', 'créature')}.
Personnalité : {', '.join(tamagotchi.get('personality', []))}.
Besoins actuels : {json.dumps(tamagotchi.get('needs', {}), ensure_ascii=False)}

Génère un PETIT événement aléatoire qui lui arrive (surprise, découverte, incident mineur...).
L'événement doit être court et fun.

Retourne un JSON:
{{
    "event": "description courte de l'événement",
    "needs": {{ ... les besoins impactés ... }},
    "xp_gained": 5
}}"""

    result = await call_ai(prompt)
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3002)
