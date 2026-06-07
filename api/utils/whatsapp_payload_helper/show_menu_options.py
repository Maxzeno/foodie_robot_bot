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
                    "title": "Meal recommendation",
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
                            "description": "View your orders"
                        }
                    ]
                },
                {
                    "title": "Your Profile",
                    "rows": [
                        {
                            "id": "view-update-profile",
                            "title": "View/Update Profile",
                            "description": "View/Update your profile info"
                        }
                    ]
                },
                {
                    "title": "Referral and Balance",
                    "rows": [
                        {
                            "id": "referral-link",
                            "title": "Referral link",
                            "description": "Get referral link"
                        },
                        {
                            "id": "show-balance",
                            "title": "Show/Withdraw balance",
                            "description": "Show/Withdraw my balance"
                        },
                        {
                            "id": "withdraw-history",
                            "title": "Withdrawal history",
                            "description": "Your withdrawal history"
                        },
                    ]
                },
                {
                    "title": "Delivery Location",
                    "rows": [
                        {
                            "id": "update-location",
                            "title": "Update delivery location",
                            "description": "Update my delivery location"
                        },
                        {
                            "id": "get-location",
                            "title": "Get delivery location",
                            "description": "Get my delivery location"
                        }
                    ]
                },
                {
                    "title": "Support",
                    "rows": [
                        # {
                        #     "id": "meal-liked-disliked",
                        #     "title": "Liked/disliked meals",
                        #     "description": "Fetch liked/disliked meals"
                        # },
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
