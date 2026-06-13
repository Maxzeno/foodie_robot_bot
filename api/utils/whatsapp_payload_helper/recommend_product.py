def recommend_product_payload(recomendation_id, body, image_url=None):
    resp = {
            "type": "button",
            "body": {
                "text": body
            },
            "footer": {
                "text": "Tap below to order or let us know what you think!"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"order-now--{recomendation_id}",
                            "title": "Order Now"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"i-love-this-meal--{recomendation_id}",
                            "title": "Love it"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"i-hate-this-meal--{recomendation_id}",
                            "title": "Not for me"
                        }
                    }
                ]
            }
        }

    if image_url:
        resp["header"] = {
            "type": "image",
            "image": {
                "link": image_url
            }
        }
    return resp
