from openai import OpenAI
from django.conf import settings


ALIBABA_CLOUD_DASHSCOPE_BASE_URL = (
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)


def get_ai_client() -> OpenAI:

    kwargs = {"api_key": settings.AI_API_KEY}
    if settings.AI_BASE_URL:
        kwargs["base_url"] = settings.AI_BASE_URL
    return OpenAI(**kwargs)
