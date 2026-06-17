from api.models.meal import Meal


def recommend_product_payload(body: str, meal: Meal):
    print("Generating recommend product payload...")
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
                            "id": "order-now",
                            "title": "Order Now"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "i-love-this-meal",
                            "title": "Love it"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "i-hate-this-meal",
                            "title": "Didn’t like it"
                        }
                    }
                ]
            }
        }
    
    get_branded_image_url = meal.get_branded_image_url
    if get_branded_image_url:
        resp["header"] = {
            "type": "image",
            "image": {
                "link": get_branded_image_url
            }
        }
    return resp
