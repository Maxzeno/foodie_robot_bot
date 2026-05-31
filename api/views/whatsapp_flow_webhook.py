from ninja import Router
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db import transaction
import json
from api.utils.whatsapp_flow_crypto import WhatsAppFlowCrypto

router = Router(tags=["Webhook"])


@csrf_exempt
@router.get("/whatsapp-flow/public-key", auth=None)
def get_public_key(request):
    """
    Endpoint to get the public key for WhatsApp Flow configuration.

    Use this public key in your WhatsApp Flow settings.
    """
    try:
        public_key = WhatsAppFlowCrypto.get_public_key_pem()
        return HttpResponse(public_key, content_type="text/plain")
    except Exception as e:
        return HttpResponse(f"Error generating public key: {str(e)}", status=500)


@csrf_exempt
@transaction.atomic
@router.post("/whatsapp-flow", auth=None)
def whatsapp_flow_webhook(request):
    """
    Handle encrypted WhatsApp Flow webhook requests.

    This endpoint:
    1. Decrypts incoming flow data
    2. Processes the flow request
    3. Encrypts and signs the response
    """
    try:
        # Parse incoming request
        request_data = json.loads(request.body)
        print("WhatsApp Flow Webhook - Raw request:", request_data)

        # Check if request is encrypted
        if 'encrypted_flow_data' not in request_data:
            # Handle unencrypted health check or verification
            print("Unencrypted request received")
            return HttpResponse("OK", status=200)

        # Extract encryption parameters
        encrypted_flow_data = request_data.get('encrypted_flow_data')
        encrypted_aes_key = request_data.get('encrypted_aes_key')
        initial_vector = request_data.get('initial_vector')

        # Decrypt the request
        decrypted_data = WhatsAppFlowCrypto.decrypt_request(
            encrypted_flow_data,
            encrypted_aes_key,
            initial_vector
        )

        print("Decrypted Flow Data:", json.dumps(decrypted_data, indent=2))

        # Process the flow data based on action
        # TODO: Implement your business logic here
        response_data = process_flow_data(decrypted_data)

        # Encrypt the response
        encrypted_response = WhatsAppFlowCrypto.encrypt_response(
            response_data,
            encrypted_aes_key,
            initial_vector
        )

        # Sign the response
        signature = WhatsAppFlowCrypto.sign_response(encrypted_response)

        # Return encrypted and signed response
        return JsonResponse({
            'encrypted_flow_data': encrypted_response,
            'signature': signature
        })

    except Exception as e:
        print(f"Error processing WhatsApp Flow webhook: {str(e)}")
        import traceback
        traceback.print_exc()

        # Return error response
        return JsonResponse({
            'error': str(e)
        }, status=500)


def process_flow_data(decrypted_data: dict) -> dict:
    """
    Process the decrypted flow data and return response.

    Args:
        decrypted_data: The decrypted flow data containing screen, data, action, etc.

    Returns:
        Response data to be encrypted and sent back
    """
    # Extract flow information
    version = decrypted_data.get('version')
    screen = decrypted_data.get('screen')
    data = decrypted_data.get('data', {})
    action = decrypted_data.get('action')
    flow_token = decrypted_data.get('flow_token')

    print(f"Processing flow - Screen: {screen}, Action: {action}")
    print(f"Data: {json.dumps(data, indent=2)}")

    # Example response structure
    # Customize this based on your flow screens and logic

    if action == 'ping':
        # Health check
        return {
            'version': version,
            'data': {
                'status': 'active'
            }
        }

    if action == 'INIT':
        # Initialize the flow
        return {
            'version': version,
            'screen': 'MENU',  # Change to your first screen
            'data': {
                'message': 'Welcome to Foodie Robot!',
                # Add your initial data here
            }
        }

    if action == 'data_exchange':
        # Handle data exchange based on screen
        if screen == 'MENU':
            # Process menu screen
            selected_option = data.get('selected_option')

            return {
                'version': version,
                'screen': 'NEXT_SCREEN',  # Navigate to next screen
                'data': {
                    # Your response data
                }
            }

        # Default response
        return {
            'version': version,
            'screen': screen,
            'data': {
                'error': 'Unknown screen or action'
            }
        }

    # Default response for unknown actions
    return {
        'version': version,
        'data': {
            'status': 'received'
        }
    }
