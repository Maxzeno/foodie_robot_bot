from api.models.user_balance import BalanceType


def get_tool_definitions():
    """Optimized tool definitions with reduced token usage."""
    return [
{
            "type": "function",
            "function": {
                "name": "save_delivery_location",
                "description": "Save delivery location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "name": {"type": "string"},
                        "address": {"type": "string"}
                    },
                    "required": ["latitude", "longitude"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "meal_recommendations",
                "description": "Generate/show personalized meal recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "request_delivery_location",
                "description": "Always use this tool when the user wants to set or update their delivery address (Very important you use this instead of prompting them to type it out)",
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
                "name": "like_or_hate_meal",
                "description": "Like or dislike a meal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {"type": "integer"},
                        "action": {
                            "type": "string",
                            "enum": ["like", "hate"]
                        }
                    },
                    "required": ["meal_id", "action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "place_order_form",
                "description": "Place meal order form used when user wants to order a meal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {"type": "integer"},
                    },
                    "required": ["meal_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "Get order status - this including the payment status (latest if no ID)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_history",
                "description": "Get order history",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"}
                    },
                    "required": []
                }
            }
        },
    {
            "type": "function",
            "function": {
                "name": "get_update_user_profile_form",
                "description": "Get or update user profile (allergies, cuisines, budget, health, fitness, view current delivery address etc.)",
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
                "name": "get_user_meal_preferences",
                "description": "Get liked or disliked meals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_liked": {"type": "boolean"},
                        "page": {"type": "integer"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "contact_support",
                "description": "Contact customer support",
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
                "name": "show_menu_options",
                "description": "Show when user wants menu options, quick actions, settings etc.",
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
                "name": "get_current_location",
                "description": "Get current delivery location",
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
                "name": "referral_link",
                "description": "Show referral link",
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
                "name": "show_balance",
                "description": "Show user balance (referral earnings etc)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "balance_type": {
                            "type": "string",
                            "enum": BalanceType.list_values()
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "make_withdrawal_form",
                "description": "Use when user wants to withdraw",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]
