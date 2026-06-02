from api.models.meal import AllergyChoices, CuisineChoices, FitnessGoalChoices, HealthConditionChoices
from api.models.user_balance import BalanceType


def get_tool_definitions():
    """Optimized tool definitions with reduced token usage."""
    return [
        {
            "type": "function",
            "function": {
                "name": "save_fitness_goal",
                "description": "Save fitness goal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fitness_goal": {
                            "type": "string",
                            "enum": FitnessGoalChoices.list_values()
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
                "description": "Save health conditions (empty array if none)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "health_conditions": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": HealthConditionChoices.list_values()
                            }
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
                "description": "Save food allergies (empty array if none)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "allergies": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": AllergyChoices.list_values()
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
                "name": "save_cuisine_preferences",
                "description": "Save cuisine preferences (empty array if none)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuisine_preferences": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": CuisineChoices.list_values()
                            }
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
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "get_nutritional_info",
        #         "description": "Get meal nutrition details",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "meal_id": {"type": "integer"}
        #             },
        #             "required": ["meal_id"]
        #         }
        #     }
        # },
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
                "name": "place_order",
                "description": "Place meal order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {"type": "integer"},
                        "number_of_plates": {"type": "integer"},
                        "special_instructions": {"type": "string"}
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
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "search_meals",
        #         "description": "Search meals by name",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "query": {"type": "string"}
        #             },
        #             "required": ["query"]
        #         }
        #     }
        # },
        {
            "type": "function",
            "function": {
                "name": "get_meal_details",
                "description": "Get meal details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meal_id": {"type": "integer"}
                    },
                    "required": ["meal_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_profile",
                "description": "Get user profile (allergies, cuisines, budget, health, fitness)",
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
                "description": "Update average meal budget",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "budget_amount": {"type": "number"}
                    },
                    "required": ["budget_amount"]
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
                    "required": ["is_liked"]
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
                "name": "review_last_ordered_meal",
                "description": "Review last ordered meal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sentiment": {
                            "type": "string",
                            "enum": ["like", "neutral", "hate"]
                        },
                        "review_text": {"type": "string"}
                    },
                    "required": ["sentiment"]
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
        }
    ]
