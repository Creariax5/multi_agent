"""
Tool: get_weather - Get weather info (simulated)
"""
import random


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city (simulated)",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
                },
                "required": ["city"]
            }
        }
    }


def execute(city: str, units: str = "celsius") -> dict:
    """Get simulated weather data"""
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
        "note": "Simulated data"
    }
