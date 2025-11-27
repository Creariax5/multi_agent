"""
Tool: generate_random - Generate random values
"""
import random
import uuid as uuid_lib


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "generate_random",
            "description": "Generate random numbers or pick random items",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["integer", "float", "choice", "uuid"]},
                    "min": {"type": "number", "description": "Min value"},
                    "max": {"type": "number", "description": "Max value"},
                    "choices": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["type"]
            }
        }
    }


def execute(type: str, min: float = None, max: float = None, choices: list = None) -> dict:
    """Generate random values"""
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
