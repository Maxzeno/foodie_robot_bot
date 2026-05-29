def number_of_plates(text: str, meal_id: str):
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
                    "title": "Select number of plates",
                    "rows": [
                        {
                            "id": f"plates--1--{meal_id}",
                            "title": "1 Plate",
                        },
                        {
                            "id": f"plates--2--{meal_id}",
                            "title": "2 Plates",
                        },
                        {
                            "id": f"plates--3--{meal_id}",
                            "title": "3 Plates",
                        },
                        {
                            "id": f"plates--4--{meal_id}",
                            "title": "4 Plates",
                        },
                        {
                            "id": f"plates--5--{meal_id}",
                            "title": "5 Plates",
                        },
                        {
                            "id": f"plates--6--{meal_id}",
                            "title": "6 Plates",
                        },
                        {
                            "id": f"plates--7--{meal_id}",
                            "title": "7 Plates",
                        },
                        {
                            "id": f"plates--8--{meal_id}",
                            "title": "8 Plates",
                        },
                        {
                            "id": f"plates--9--{meal_id}",
                            "title": "9 Plates",
                        },
                        {
                            "id": f"plates--10--{meal_id}",
                            "title": "10 Plates",
                        },
                        
                    ]
                    
                }
            ]
        }
    }
