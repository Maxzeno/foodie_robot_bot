def show_menu_options_payload(text):
    return {
        "type": "list",
        "body": {
            "text": text,
        },
        "footer": {
            "text": "Select an option to proceed"
        },
        "action": {
            "button": "Quick Options",
            "sections": [
                {
                    "title": "Meals & Recommendations",
                    "rows": [
                        {
                            "id": "meal-recommendations",
                            "title": "Get Meal Recommendations",
                            "description": "Get personalized meal suggestions"
                        }
                    ]
                },
                {
                    "title": "Orders",
                    "rows": [
                        {
                            "id": "view-orders",
                            "title": "View Order History",
                            "description": "View your past orders"
                        },
                        {
                            "id": "order-status",
                            "title": "Current Order Status",
                            "description": "Track your current order"
                        }
                    ]
                },
                {
                    "title": "Profile",
                    "rows": [
                        {
                            "id": "view-profile",
                            "title": "View Profile",
                            "description": "View your profile info"
                        },
                    ]
                },
                {
                    "title": "Update Preferences",
                    "rows": [
                        {
                            "id": "update-allergies",
                            "title": "Update Allergies",
                            "description": "Update food allergies"
                        },
                        {
                            "id": "update-health",
                            "title": "Update Health Conditions",
                            "description": "Update health conditions"
                        },
                        {
                            "id": "update-fitness",
                            "title": "Update Fitness Goals",
                            "description": "Update fitness goals"
                        },
                        {
                            "id": "update-cuisine",
                            "title": "Update Preferred Cuisine",
                            
                            "description": "Update cuisine preferences"
                        },
                        {
                            "id": "update-budget",
                            "title": "Update Average Budget",
                            "description": "Set meal budget"
                        }
                    ]
                },
                {
                    "title": "Support",
                    "rows": [
                        {
                            "id": "contact-support",
                            "title": "Contact Support",
                            "description": "Get help from customer support"
                        }
                    ]
                }
            ]
        }
    }
