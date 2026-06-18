from django.utils.crypto import get_random_string
import random


def generate_unique_code(model, field, length=8):
    allowed_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    unique_code = get_random_string(length=length, allowed_chars=allowed_chars)

    # Dynamically filter the model using the provided field
    filter_kwargs = {field: unique_code}
    while model.objects.filter(**filter_kwargs).exists():
        unique_code = get_random_string(length=length, allowed_chars=allowed_chars)
    return unique_code.lower()


def generate_confirmation_code():
    """Generate 4-digit confirmation code for order delivery."""
    return str(random.randint(1000, 9999))

