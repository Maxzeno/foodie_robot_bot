"""
Simple AI tools for onboarding - minimal token usage
"""

# Minimal tool definitions
ONBOARDING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_fitness_goal",
            "description": "Save user's fitness goal (weight_loss, muscle_gain, or maintenance)",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "enum": ["weight_loss", "muscle_gain", "maintenance"],
                        "description": "Fitness goal"
                    }
                },
                "required": ["goal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_health_conditions",
            "description": "Save health conditions like diabetes, hypertension. Use empty array if none.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["diabetes", "hypertension", "high_cholesterol", "anemia", "celiac", "lactose_intolerance"]
                        }
                    }
                },
                "required": ["conditions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_allergies",
            "description": "Save food allergies. Use empty array if none.",
            "parameters": {
                "type": "object",
                "properties": {
                    "allergies": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["peanuts", "seafood", "dairy", "gluten", "eggs", "soy", "tree_nuts"]
                        }
                    }
                },
                "required": ["allergies"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_cuisines",
            "description": "Save preferred cuisines",
            "parameters": {
                "type": "object",
                "properties": {
                    "cuisines": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["nigerian", "ghanaian", "ethiopian", "moroccan", "italian", "french", "spanish",
                                   "greek", "british", "chinese", "japanese", "korean", "thai", "indian", "vietnamese",
                                   "filipino", "american", "mexican", "brazilian", "argentinian", "caribbean", "vegan_vegetarian"]
                        }
                    }
                },
                "required": ["cuisines"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_location",
            "description": "Request user's delivery location. ALWAYS use this - never ask to type address.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "Get meal recommendations for user (after onboarding complete)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
