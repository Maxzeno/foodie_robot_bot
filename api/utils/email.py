import requests
from django.conf import settings


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    from_email: str = "noreply@foodierobot.com",
):
    url = "https://api.zeptomail.com/v1.1/email"

    payload = {
        "from": {"address": from_email},
        "to": [
            {
                "email_address": {
                    "address": to_email,
                    "name": to_name,
                }
            }
        ],
        "subject": subject,
        "htmlbody": html_body,
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": settings.ZOHO_ZEPTOMAIL_KEY,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json(),
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "response": getattr(response, "text", None),
        }
