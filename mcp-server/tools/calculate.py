"""
Tool: calculate - Perform mathematical calculations
"""
import math


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expression to evaluate (e.g., '2+2', 'sqrt(16)')"
                    }
                },
                "required": ["expression"]
            }
        }
    }


def execute(expression: str) -> dict:
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
