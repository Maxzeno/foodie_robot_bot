def recommend_product_payload(meal_id, body, image_url):
    return {
            "type": "button",
            "header": {
                "type": "image",
                "image": {
                    "link": image_url
                }
            },
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
                            "id": f"order-now--{meal_id}",
                            "title": "Order now"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"i-love-this-meal--{meal_id}",
                            "title": "I love this meal"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"i-hate-this-meal--{meal_id}",
                            "title": "I hate this meal"
                        }
                    }
                ]
            }
        }
