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
                "description": "Save user's delivery location and detect the city based on the coordinates",
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
                "description": "Generate personalized meal recommendations",
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
                "description": "Request the user to share their delivery location via WhatsApp location sharing feature",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "like_or_hate_meal",
                "description": "Like or hate meal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {
                            "type": "integer",
                            "description": "ID of the meal"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["like", "hate"],
                            "description": "Like or hate meal depends on action"
                        }
                    },
                    "required": ["meal_id", "action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "place_order",
                "description": "Place an order for a meal with specified quantity (number of plates)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {
                            "type": "integer",
                            "description": "ID of the meal to order"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Number of plates to order (default: 1)"
                        },
                        "delivery_address_id": {
                            "type": "integer",
                            "description": "Specific delivery address ID (optional, uses default if not provided)"
                        },
                        "special_instructions": {
                            "type": "string",
                            "description": "Special requests or notes for the order (optional)"
                        }
                    },
                    "required": ["meal_id", "quantity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "Get the status of a specific order or the latest order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "ID of the order to check (optional, gets latest order if not provided)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_history",
                "description": "Get user's order history with pagination",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "description": "Page number to retrieve (default: 1)"
                        },
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_meals",
                "description": "Search for meals by name or description (returns max 5 results)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term for meal name or description"
                        },
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_meal_details",
                "description": "Get complete details about a specific meal including nutrition, price, and availability",
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
                "name": "get_user_profile",
                "description": "Get user's profile including allergies, preferred cuisines, average budget, health conditions, and fitness goal",
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
                "name": "update_average_budget",
                "description": "Update user's average meal budget (currency depends on user's city)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "budget_amount": {
                            "type": "number",
                            "description": "New average budget amount per meal"
                        }
                    },
                    "required": ["budget_amount"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_meal_preferences",
                "description": "Get meals that user has liked or hated/disliked",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_liked": {
                            "type": "boolean",
                            "description": "is liked if true else disliked"
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number to retrieve (default: 1)"
                        },
                    },
                    "required": ["is_liked"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_payment_status",
                "description": "Get payment status for the latest order. Use when user asks 'have I paid?' or 'is my payment confirmed?'",
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
                "name": "contact_support",
                "description": "Contact customer support with an issue or question",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "review_last_ordered_meal",
                "description": "Submit a review for a meal that was ordered. Sentiment can be like, neutral, or hate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sentiment": {
                            "type": "string",
                            "enum": ["like", "neutral", "hate"],
                            "description": "User's sentiment about the meal"
                        },
                        "review_text": {
                            "type": "string",
                            "description": "Optional review comment from user"
                        },
                    },
                    "required": ["sentiment"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_location",
                "description": "Get user's current delivery location",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                    "required": []
                }
            }
        }
    ]
