from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
import os

app = FastAPI(title="AI 20 Questions")

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
                    {"role": "system", "content": "Tu joues à 20 Questions. Retourne UNIQUEMENT du JSON valide, sans markdown."},
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


@app.post("/api/new-game")
async def new_game(request: Request):
    """Start a new game - AI picks something to guess"""
    body = await request.json()
    category = body.get("category", "objet")
    difficulty = body.get("difficulty", "moyen")

    prompt = f"""Tu vas jouer à 20 Questions. Choisis un(e) {category} à faire deviner.
Difficulté: {difficulty}
- Facile = très connu, courant
- Moyen = connu mais pas évident
- Difficile = existe mais obscur

Retourne un JSON:
{{
    "answer": "la réponse exacte",
    "category": "{category}",
    "difficulty": "{difficulty}",
    "hint": "un indice très vague pour commencer"
}}

Choisis quelque chose d'intéressant et amusant à deviner!"""

    result = await call_ai(prompt)
    return JSONResponse(result)


@app.post("/api/ask")
async def ask_question(request: Request):
    """Ask a yes/no question"""
    body = await request.json()
    answer = body.get("answer", "")
    question = body.get("question", "")
    history = body.get("history", [])

    history_text = "\n".join([f"Q: {h['q']} → R: {h['r']}" for h in history[-10:]])

    prompt = f"""Tu joues à 20 Questions. La réponse secrète est: "{answer}"

Historique des questions:
{history_text if history_text else "(aucune question encore)"}

Nouvelle question: "{question}"

Réponds honnêtement à cette question par rapport à "{answer}".
Retourne un JSON:
{{
    "response": "Oui",
    "explanation": ""
}}
response peut être: "Oui", "Non", "Partiellement", ou "Ça dépend"."""

    result = await call_ai(prompt)
    if "error" in result:
        result = {"response": "Hmm...", "explanation": "Je ne suis pas sûr"}
    return JSONResponse(result)


@app.post("/api/guess")
async def check_guess(request: Request):
    """Check if the player's guess is correct"""
    body = await request.json()
    answer = body.get("answer", "")
    guess = body.get("guess", "")

    prompt = f"""La réponse secrète est: "{answer}"
Le joueur propose: "{guess}"

Est-ce correct? Accepte les formulations proches (singulier/pluriel, avec/sans article, synonymes proches).

Retourne un JSON:
{{
    "correct": true,
    "message": "Bravo! C'était bien {answer}!"
}}
Mets correct à false si la réponse est fausse."""

    result = await call_ai(prompt)
    if "error" in result:
        result = {"correct": False, "message": "Je n'ai pas compris ta réponse"}
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3003)
