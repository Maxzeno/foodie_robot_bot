import json
from base64 import b64decode, b64encode

from ninja import Router
from django.http import HttpResponse, JsonResponse

from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import requests
from django.conf import settings


router = Router(tags=["Webhook"])


def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
    # Load private key path from environment variable, fallback to default path
    private_key_path = settings.WHATSAPP_FLOW_PRIVATE_KEY_PATH

    # Read the private key from the file
    with open(private_key_path, "r") as f:
        PRIVATE_KEY = f.read()

    flow_data = b64decode(encrypted_flow_data_b64)
    iv = b64decode(initial_vector_b64)

    # Decrypt the AES encryption key
    encrypted_aes_key = b64decode(encrypted_aes_key_b64)
    private_key = load_pem_private_key(
        PRIVATE_KEY.encode('utf-8'), password=None)
    aes_key = private_key.decrypt(encrypted_aes_key, OAEP(
        mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

    # Decrypt the Flow data
    encrypted_flow_data_body = flow_data[:-16]
    encrypted_flow_data_tag = flow_data[-16:]
    decryptor = Cipher(algorithms.AES(aes_key),
                       modes.GCM(iv, encrypted_flow_data_tag)).decryptor()
    decrypted_data_bytes = decryptor.update(
        encrypted_flow_data_body) + decryptor.finalize()
    decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
    return decrypted_data, aes_key, iv


def encrypt_response(response, aes_key, iv):
    # Flip the initialization vector
    flipped_iv = bytearray()
    for byte in iv:
        flipped_iv.append(byte ^ 0xFF)

    # Encrypt the response data
    encryptor = Cipher(algorithms.AES(aes_key),
                       modes.GCM(flipped_iv)).encryptor()
    return b64encode(
        encryptor.update(json.dumps(response).encode("utf-8")) +
        encryptor.finalize() +
        encryptor.tag
    ).decode("utf-8")


@csrf_exempt
@transaction.atomic
@router.post("/whatsapp-flow", auth=None)
def flow_handler(request):
    print("Flow Webhook", request.body)

    # Parse the webhook payload
    try:
        payload = json.loads(request.body.decode("utf-8"))

        encrypted_flow_data = payload["encrypted_flow_data"]
        encrypted_aes_key = payload["encrypted_aes_key"]
        initial_vector = payload["initial_vector"]

        # 🔓 Decrypt incoming data
        decrypted_data, aes_key, iv = decrypt_request(
            encrypted_flow_data,
            encrypted_aes_key,
            initial_vector
        )

        print("DECRYPTED FLOW DATA:", decrypted_data)

        # Prepare next screen response
        # response = {
        #     "screen": "SCREEN_NAME",   # 👈 Change this to your real screen
        #     "data": {
        #         "some_key": "some_value"
        #     }
        # }

        response = {"data": {"status": "active"}}

        encrypted_output = encrypt_response(response, aes_key, iv)

        return HttpResponse(
            encrypted_output,
            content_type="text/plain"
        )

    except Exception as e:
        print("FLOW ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)


@router.post("/upload-public-key")
def upload_public_key(request):
    # Load public key path from environment variable, fallback to default path
    public_key_path = settings.WHATSAPP_FLOW_PUBLIC_KEY_PATH

    # Read the public key from the file
    with open(public_key_path, "r") as f:
        public_key_str = f.read()

    url = f"https://graph.facebook.com/v24.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/whatsapp_business_encryption"

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "business_public_key": public_key_str
    }

    response = requests.post(url, headers=headers, data=data)

    return response.json()
