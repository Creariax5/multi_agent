import os
import httpx
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080/v1")
CACHE_FILE = "craft_cache.json"
craft_cache = {}

def load_cache():
    global craft_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                craft_cache = json.load(f)
            print(f"Loaded {len(craft_cache)} recipes from cache")
        except Exception as e:
            print(f"Failed to load cache: {e}")
            craft_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(craft_cache, f, indent=2)
    except Exception as e:
        print(f"Failed to save cache: {e}")

load_cache()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/combine")
async def combine(request: Request):
    data = await request.json()
    element1 = data.get("element1")
    element2 = data.get("element2")
    
    if not element1 or not element2:
        return JSONResponse({"error": "Missing elements"}, status_code=400)

    # Check cache
    cache_key = " + ".join(sorted([element1, element2]))
    if cache_key in craft_cache:
        print(f"Cache hit: {cache_key} -> {craft_cache[cache_key]['result']}")
        return JSONResponse(craft_cache[cache_key])

    system_prompt = """You are the engine for the game Infinite Craft. 
Your goal is to combine two elements to create a new one.
Rules:
1. Result should be a single noun or short phrase.
2. Result should be logical, punny, or creative.
3. You MUST return a valid JSON object with these fields:
   - "result": The name of the new element (string)
   - "emoji": A single emoji representing the new element (string)
   - "is_new": boolean (always false for now, but required field)
4. If the combination doesn't make sense, try to find a loose association.
5. IMPORTANT: Return ONLY the JSON object. No markdown, no explanations.

Examples:
User: Combine: Fire + Water
Assistant: {"result": "Steam", "emoji": "💨", "is_new": false}
"""

    user_prompt = f"Combine: {element1} + {element2}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{COPILOT_PROXY_URL}/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "use_tools": False
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_detail = json.dumps(error_json["error"])
                except:
                    pass
                return JSONResponse({"error": f"Copilot Proxy Error ({response.status_code}): {error_detail}"}, status_code=500)
            
            result_json = response.json()
            content = result_json["choices"][0]["message"]["content"]
            print(f"DEBUG: Raw content from AI: {content}")
            
            # Parse the content as JSON
            try:
                # Try to find JSON object boundaries
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx:end_idx+1]
                    craft_result = json.loads(json_str)
                    
                    # Save to cache
                    craft_cache[cache_key] = craft_result
                    save_cache()
                    
                    return JSONResponse(craft_result)
                else:
                    raise ValueError("No JSON object found")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"ERROR: Failed to parse JSON: {e}")
                # Fallback if JSON parsing fails
                return JSONResponse({
                    "result": content[:20], 
                    "emoji": "❓", 
                    "is_new": False
                })

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
