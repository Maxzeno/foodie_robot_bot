def pick_delivery_option(meal_id, body):
    return {
            "type": "button",
            # "header": {
            #     "type": "image",
            #     "image": {
            #         "link": image_url
            #     }
            # },
            "body": {
                "text": body
            },
            # "footer": {
            #     "text": "Hola"
            # },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"current-address--{meal_id}",
                            "title": "Use Current Address"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"new-address--{meal_id}",
                            "title": "Use a new address"
                        }
                    },
                     {
                        "type": "reply",
                        "reply": {
                            "id": "see-all-manu-options",
                            "title": "See all manu options"
                        }
                    }
                ]
            }
        }
