"""
MCP Server - Provides tools for AI agents
Exposes various utility functions as MCP-compatible tools
"""
import os
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import math

app = FastAPI(title="MCP Tools Server")


# ============================================================================
# TOOL DEFINITIONS (OpenAI function calling format)
# ============================================================================

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in various formats",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'Europe/Paris', 'UTC'). Default is UTC.",
                        "default": "UTC"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'iso', 'human', 'unix'. Default is 'human'.",
                        "enum": ["iso", "human", "unix"],
                        "default": "human"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations. Supports basic operations, trigonometry, logarithms, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sin(pi/2)', 'sqrt(16)')"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather information for a city (simulated data for demo)",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'Paris', 'New York')"
                    },
                    "units": {
                        "type": "string",
                        "description": "Temperature units: 'celsius' or 'fahrenheit'",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information (simulated results for demo)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-5)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_units",
            "description": "Convert between different units of measurement",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "The numeric value to convert"
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "Source unit (e.g., 'km', 'miles', 'kg', 'pounds', 'celsius', 'fahrenheit')"
                    },
                    "to_unit": {
                        "type": "string",
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_random",
            "description": "Generate random numbers or pick random items",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of random generation",
                        "enum": ["integer", "float", "choice", "uuid"]
                    },
                    "min": {
                        "type": "number",
                        "description": "Minimum value (for integer/float)"
                    },
                    "max": {
                        "type": "number",
                        "description": "Maximum value (for integer/float)"
                    },
                    "choices": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of items to pick from (for choice type)"
                    }
                },
                "required": ["type"]
            }
        }
    }
]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def tool_get_current_time(timezone: str = "UTC", format: str = "human") -> dict:
    """Get current time"""
    now = datetime.utcnow()
    
    if format == "iso":
        return {"time": now.isoformat() + "Z", "timezone": timezone}
    elif format == "unix":
        return {"timestamp": int(now.timestamp()), "timezone": timezone}
    else:  # human
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day": now.strftime("%A"),
            "timezone": timezone
        }


def tool_calculate(expression: str) -> dict:
    """Evaluate mathematical expression"""
    # Safe math functions
    safe_dict = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
        "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
        "pi": math.pi, "e": math.e,
        "degrees": math.degrees, "radians": math.radians
    }
    
    try:
        # Clean expression
        expr = expression.replace("^", "**")
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": f"Invalid expression: {str(e)}"}


def tool_get_weather(city: str, units: str = "celsius") -> dict:
    """Get simulated weather data"""
    import random
    
    # Simulated weather data
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy"]
    base_temp = random.randint(5, 30)
    
    if units == "fahrenheit":
        temp = base_temp * 9/5 + 32
        temp_unit = "°F"
    else:
        temp = base_temp
        temp_unit = "°C"
    
    return {
        "city": city,
        "temperature": round(temp, 1),
        "unit": temp_unit,
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 90),
        "wind_speed": random.randint(0, 50),
        "wind_unit": "km/h",
        "note": "This is simulated data for demonstration purposes"
    }


def tool_search_web(query: str, num_results: int = 3) -> dict:
    """Return simulated search results"""
    # Simulated search results
    results = [
        {
            "title": f"Result {i+1} for: {query}",
            "url": f"https://example.com/search/{query.replace(' ', '-')}/{i+1}",
            "snippet": f"This is a simulated search result #{i+1} for the query '{query}'. In a real implementation, this would contain actual web search results."
        }
        for i in range(min(num_results, 5))
    ]
    
    return {
        "query": query,
        "num_results": len(results),
        "results": results,
        "note": "These are simulated results for demonstration purposes"
    }


def tool_convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert between units"""
    conversions = {
        # Length
        ("km", "miles"): lambda x: x * 0.621371,
        ("miles", "km"): lambda x: x * 1.60934,
        ("m", "feet"): lambda x: x * 3.28084,
        ("feet", "m"): lambda x: x * 0.3048,
        ("cm", "inches"): lambda x: x * 0.393701,
        ("inches", "cm"): lambda x: x * 2.54,
        
        # Weight
        ("kg", "pounds"): lambda x: x * 2.20462,
        ("pounds", "kg"): lambda x: x * 0.453592,
        ("g", "oz"): lambda x: x * 0.035274,
        ("oz", "g"): lambda x: x * 28.3495,
        
        # Temperature
        ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
        ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
        ("celsius", "kelvin"): lambda x: x + 273.15,
        ("kelvin", "celsius"): lambda x: x - 273.15,
        
        # Volume
        ("liters", "gallons"): lambda x: x * 0.264172,
        ("gallons", "liters"): lambda x: x * 3.78541,
    }
    
    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        result = conversions[key](value)
        return {
            "original": {"value": value, "unit": from_unit},
            "converted": {"value": round(result, 4), "unit": to_unit}
        }
    else:
        return {"error": f"Conversion from {from_unit} to {to_unit} not supported"}


def tool_generate_random(type: str, min: float = None, max: float = None, choices: list = None) -> dict:
    """Generate random values"""
    import random
    import uuid as uuid_lib
    
    if type == "integer":
        min_val = int(min) if min is not None else 0
        max_val = int(max) if max is not None else 100
        return {"type": "integer", "value": random.randint(min_val, max_val)}
    
    elif type == "float":
        min_val = float(min) if min is not None else 0.0
        max_val = float(max) if max is not None else 1.0
        return {"type": "float", "value": round(random.uniform(min_val, max_val), 6)}
    
    elif type == "choice":
        if not choices:
            return {"error": "No choices provided"}
        return {"type": "choice", "value": random.choice(choices)}
    
    elif type == "uuid":
        return {"type": "uuid", "value": str(uuid_lib.uuid4())}
    
    else:
        return {"error": f"Unknown type: {type}"}


# Tool registry
TOOL_FUNCTIONS = {
    "get_current_time": tool_get_current_time,
    "calculate": tool_calculate,
    "get_weather": tool_get_weather,
    "search_web": tool_search_web,
    "convert_units": tool_convert_units,
    "generate_random": tool_generate_random,
}


# ============================================================================
# API ENDPOINTS
# ============================================================================

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolCallBatchRequest(BaseModel):
    tool_calls: List[Dict[str, Any]]


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "MCP Tools Server",
        "available_tools": list(TOOL_FUNCTIONS.keys())
    }


@app.get("/tools")
async def get_tools():
    """Return all available tools in OpenAI function format"""
    return {"tools": AVAILABLE_TOOLS}


@app.post("/execute")
async def execute_tool(request: ToolCallRequest):
    """Execute a single tool"""
    tool_name = request.name
    arguments = request.arguments
    
    if tool_name not in TOOL_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        result = TOOL_FUNCTIONS[tool_name](**arguments)
        return {"tool": tool_name, "result": result}
    except Exception as e:
        return {"tool": tool_name, "error": str(e)}


@app.post("/execute_batch")
async def execute_tools_batch(request: ToolCallBatchRequest):
    """Execute multiple tool calls (for parallel tool calling)"""
    results = []
    
    for tool_call in request.tool_calls:
        tool_id = tool_call.get("id", "unknown")
        function = tool_call.get("function", {})
        tool_name = function.get("name", "")
        
        # Parse arguments
        arguments_str = function.get("arguments", "{}")
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            arguments = {}
        
        if tool_name not in TOOL_FUNCTIONS:
            results.append({
                "tool_call_id": tool_id,
                "role": "tool",
                "content": json.dumps({"error": f"Tool '{tool_name}' not found"})
            })
            continue
        
        try:
            result = TOOL_FUNCTIONS[tool_name](**arguments)
            results.append({
                "tool_call_id": tool_id,
                "role": "tool",
                "content": json.dumps(result)
            })
        except Exception as e:
            results.append({
                "tool_call_id": tool_id,
                "role": "tool",
                "content": json.dumps({"error": str(e)})
            })
    
    return {"results": results}


@app.get("/health")
async def health():
    return {"status": "healthy"}
