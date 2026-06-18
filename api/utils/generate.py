from django.utils.crypto import get_random_string
import string

def generate_unique_code(model, field, length=8):
    allowed_chars = string.ascii_uppercase + string.digits
    unique_code = get_random_string(length=length, allowed_chars=allowed_chars)

    # Dynamically filter the model using the provided field
    filter_kwargs = {field: unique_code}
    while model.objects.filter(**filter_kwargs).exists():
        unique_code = get_random_string(length=length, allowed_chars=allowed_chars)
    return unique_code.lower()


def generate_confirmation_code(length=5):
    """Generate 5-character lowercase alphanumeric confirmation code."""
    chars = string.ascii_uppercase + string.digits
    return get_random_string(length=length, allowed_chars=chars)
