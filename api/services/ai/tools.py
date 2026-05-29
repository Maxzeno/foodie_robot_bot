"""
OpenAI function/tool definitions for the food recommendation bot.
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_recommendations",
            "description": "Retrieve the user's meal recommendations for today. Can filter by time period (morning, afternoon, evening).",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_period": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening", "all"],
                        "description": "The time period to get recommendations for. Use 'all' to get all recommendations for the day."
                    }
                },
                "required": ["time_period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Get the user's profile information including preferences, allergies, fitness goals, and budget.",
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
            "name": "create_order",
            "description": "Create a new order for a meal. Requires meal ID, quantity, and delivery address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {
                        "type": "integer",
                        "description": "The ID of the meal to order"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of plates to order",
                        "minimum": 1
                    },
                    "delivery_address": {
                        "type": "string",
                        "description": "The delivery address for the order"
                    }
                },
                "required": ["meal_id", "quantity", "delivery_address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_preferences",
            "description": "Update user preferences such as fitness goals, budget, allergies, or preferred cuisines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fitness_goal": {
                        "type": "string",
                        "description": "New fitness goal (e.g., 'Weight Loss', 'Muscle Gain', 'Maintenance')"
                    },
                    "budget": {
                        "type": "number",
                        "description": "Average meal budget in Naira"
                    },
                    "allergies_to_add": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of allergies to add"
                    },
                    "allergies_to_remove": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of allergies to remove"
                    },
                    "cuisines_to_add": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of preferred cuisines to add"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get the status of a specific order or the user's recent orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "Specific order ID to check. If not provided, returns recent orders."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_delivery_location",
            "description": "Request the user to share their delivery location using WhatsApp's interactive map picker. Use this when you need a delivery address for an order. DO NOT ask users to type addresses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {
                        "type": "integer",
                        "description": "The ID of the meal being ordered (for context)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for requesting location (e.g., 'to complete your order', 'to add delivery address')"
                    }
                },
                "required": ["meal_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_previous_orders",
            "description": "Get the user's order history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of orders to return (default 5)",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_meal_feedback",
            "description": "Record whether the user likes or dislikes a meal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {
                        "type": "integer",
                        "description": "The ID of the meal"
                    },
                    "liked": {
                        "type": "boolean",
                        "description": "True if user likes the meal, False if they don't"
                    }
                },
                "required": ["meal_id", "liked"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_user_location",
            "description": "Request the user to share their location using WhatsApp's interactive location picker. ALWAYS use this as the FIRST step in onboarding to get their city and set currency. Never ask users to type location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for requesting location (e.g., 'to determine your city and available meals', 'to set up your account')",
                        "default": "to determine your city and currency"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_fitness_goal",
            "description": "Set or update the user's fitness goal based on their input (e.g., 'weight loss', 'muscle gain', 'maintenance', 'general health').",
            "parameters": {
                "type": "object",
                "properties": {
                    "fitness_goal": {
                        "type": "string",
                        "description": "The fitness goal name (e.g., 'Weight Loss', 'Muscle Gain', 'Maintenance', 'General Health')"
                    }
                },
                "required": ["fitness_goal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_health_conditions",
            "description": "Set the user's health conditions from their natural language input (e.g., 'diabetes', 'high blood pressure', 'none').",
            "parameters": {
                "type": "object",
                "properties": {
                    "health_conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of health conditions mentioned by the user. Use empty array if user says 'none' or 'no health conditions'."
                    }
                },
                "required": ["health_conditions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_allergies",
            "description": "Set the user's food allergies from their natural language input (e.g., 'peanuts', 'shellfish', 'lactose', 'none').",
            "parameters": {
                "type": "object",
                "properties": {
                    "allergies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of food allergies mentioned by the user. Use empty array if user says 'none' or 'no allergies'."
                    }
                },
                "required": ["allergies"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_preferred_cuisines",
            "description": "Set the user's preferred cuisines from their natural language input (e.g., 'Italian', 'Chinese', 'Nigerian', 'Mexican').",
            "parameters": {
                "type": "object",
                "properties": {
                    "cuisines": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of cuisine preferences mentioned by the user"
                    }
                },
                "required": ["cuisines"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_budget",
            "description": "Set the user's average meal budget. This should be called AFTER location is set since currency depends on the user's city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {
                        "type": "number",
                        "description": "Average meal budget amount in the user's local currency"
                    }
                },
                "required": ["budget"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_onboarding_status",
            "description": "Check which onboarding steps the user has completed. Use this to determine what information is still needed.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


class ToolRegistry:
    """Registry of available tools for the AI"""

    @staticmethod
    def get_all_tools():
        """Get all tool definitions"""
        return TOOL_DEFINITIONS

    @staticmethod
    def get_tool_names():
        """Get list of all tool function names"""
        return [tool["function"]["name"] for tool in TOOL_DEFINITIONS]

    @staticmethod
    def get_tool_by_name(name: str):
        """Get a specific tool definition by name"""
        for tool in TOOL_DEFINITIONS:
            if tool["function"]["name"] == name:
                return tool
        return None
