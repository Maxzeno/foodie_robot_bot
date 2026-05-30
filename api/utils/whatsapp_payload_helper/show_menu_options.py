def show_menu_options(text):
    return {
        "type": "list",
        # "header": {
        #     "type": "text",
        #     "text": "<MESSAGE_HEADER_TEXT>"
        # },
        "body": {
            "text": text,
        },
        # "footer": {
        #     "text": "<MESSAGE_FOOTER_TEXT>"
        # },
        "action": {
            "button": "Options",
            "sections": [
                {
                    "title": "User profile",
                    "rows": [
                        {
                            "id": "update-preference",
                            "title": "Update Preferences",
                            "description": "Update your food preferences, allergies, fitness goals, etc"
                        }
                    ]
                },
                {
                    "title": "Order",
                    "rows": [
                        {
                            "id": "view-orders",
                            "title": "View Orders",
                        },
                        {
                            "id": "order-current-recommendation",
                            "title": "Current Recommendation",
                        }
                    ]
                },
                {
                    "title": "Meal Likes and Dislikes",
                    "rows": [
                        {
                            "id": "view-liked-meals",
                            "title": "View Liked Meals",
                        },
                        {
                            "id": "view-hate-meals",
                            "title": "View Disliked Meals",
                        }
                    ]
                }
            ]
        }
    }
