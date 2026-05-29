def get_tool_definitions():
    """Returns the list of tool definitions for OpenAI function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "save_fitness_goal",
                "description": "Save user's fitness goal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fitness_goal": {
                            "type": "string",
                            "enum": ["weight_loss", "muscle_gain", "maintenance"],
                            "description": "User's fitness goal"
                        }
                    },
                    "required": ["fitness_goal"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_health_conditions",
                "description": "Save user's health conditions/issues",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "health_conditions": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["diabetes", "hypertension", "high_cholesterol", "anemia", "celiac", "lactose_intolerance"]
                            },
                            "description": "List of user's health conditions"
                        }
                    },
                    "required": ["health_conditions"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_allergies",
                "description": "Save user's food allergies",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "allergies": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["peanuts", "seafood", "dairy", "gluten", "eggs", "soy", "tree_nuts"]
                            },
                            "description": "List of food allergies"
                        }
                    },
                    "required": ["allergies"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_cuisine_preferences",
                "description": "Save user's preferred cuisines",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuisine_preferences": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "vegan_vegetarian", "nigerian", "ghanaian", "ethiopian", "moroccan",
                                    "italian", "french", "spanish", "greek", "british",
                                    "chinese", "japanese", "korean", "thai", "indian", "vietnamese", "filipino",
                                    "american", "mexican", "brazilian", "argentinian", "caribbean"
                                ]
                            },
                            "description": "List of preferred cuisines"
                        }
                    },
                    "required": ["cuisine_preferences"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_delivery_location",
                "description": "Save user's delivery location and detect the city. This will update the user's city based on the coordinates. If location is not in a supported city, user will be notified.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude of delivery location"
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude of delivery location"
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the location (e.g., Home, Work, etc.)"
                        },
                        "address": {
                            "type": "string",
                            "description": "Street address or description of location"
                        }
                    },
                    "required": ["latitude", "longitude"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_meal_recommendations",
                "description": "Generate personalized meal recommendations for the current time period (morning, afternoon, or evening)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_of_day": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "evening"],
                            "description": "Which meal time to generate recommendations for"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_nutritional_info",
                "description": "Get detailed nutritional information for a specific meal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {
                            "type": "integer",
                            "description": "ID of the meal"
                        }
                    },
                    "required": ["meal_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "request_delivery_location",
                "description": "Use this to request the user to share their delivery location via WhatsApp location sharing feature. This is needed if the user has not provided a delivery location yet or wants to add a new delivery location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_to_user": {
                            "type": "string",
                            "description": "The message to send to the user telling them to share their location. examples: We haved Saved your fitness goals now please share your delivery location. or Please share your delivery location so I can save it. etc"
                        },
                    },
                    "required": ["message_to_user"]
                }
            }
        }
    ]
