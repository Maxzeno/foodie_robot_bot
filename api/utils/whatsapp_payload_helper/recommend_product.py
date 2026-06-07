def recommend_product_payload(recomendation_id, body, image_url=None):
    resp = {
            "type": "button",
            "body": {
                "text": body
            },
            "footer": {
                "text": "Order now or share your feedback below"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"order-now--{recomendation_id}",
                            "title": "Order now"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"i-love-this-meal--{recomendation_id}",
                            "title": "I love this meal"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"i-hate-this-meal--{recomendation_id}",
                            "title": "I hate this meal"
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
    print(resp)
    return resp
