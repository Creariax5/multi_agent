"""
Tool: convert_units - Convert between units of measurement
"""


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "convert_units",
            "description": "Convert between units of measurement",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Value to convert"},
                    "from_unit": {"type": "string", "description": "Source unit"},
                    "to_unit": {"type": "string", "description": "Target unit"}
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    }


def execute(value: float, from_unit: str, to_unit: str) -> dict:
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
