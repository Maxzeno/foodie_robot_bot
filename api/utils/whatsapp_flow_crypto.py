"""
WhatsApp Flow Cryptography Utilities

This module handles encryption, decryption, and signing for WhatsApp Flows.
It's designed to work seamlessly on platforms like Render with minimal setup.

Setup:
1. Generate a private key: openssl genrsa -out private.key 2048
2. Add the private key to your environment variable as WHATSAPP_FLOW_PRIVATE_KEY
3. The public key will be auto-generated and available at /webhook/whatsapp-flow/public-key
"""

import base64
import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from django.conf import settings
import os


class WhatsAppFlowCrypto:
    """Handle WhatsApp Flow encryption, decryption, and signing."""

    _private_key = None
    _public_key = None

    @classmethod
    def _load_keys(cls):
        """Load or generate RSA keys from environment."""
        if cls._private_key is not None:
            return

        # Get private key from environment
        private_key_pem = os.getenv('WHATSAPP_FLOW_PRIVATE_KEY', '')

        if not private_key_pem:
            # For development only - generate a key pair
            print("WARNING: No WHATSAPP_FLOW_PRIVATE_KEY found. Generating temporary keys for development.")
            print("For production, set WHATSAPP_FLOW_PRIVATE_KEY environment variable.")
            cls._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        else:
            # Handle different formats of private key in env var
            if '\\n' in private_key_pem:
                private_key_pem = private_key_pem.replace('\\n', '\n')

            if not private_key_pem.startswith('-----BEGIN'):
                # Assume it's base64 encoded
                try:
                    private_key_pem = base64.b64decode(private_key_pem).decode('utf-8')
                except Exception:
                    pass

            # Load the private key
            cls._private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )

        # Generate public key from private key
        cls._public_key = cls._private_key.public_key()

    @classmethod
    def get_public_key_pem(cls) -> str:
        """Get the public key in PEM format for WhatsApp Flow configuration."""
        cls._load_keys()
        pem = cls._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')

    @classmethod
    def decrypt_request(cls, encrypted_flow_data_b64: str, encrypted_aes_key_b64: str, initial_vector_b64: str) -> Dict[str, Any]:
        """
        Decrypt an incoming WhatsApp Flow request.

        Args:
            encrypted_flow_data_b64: Base64 encoded encrypted data
            encrypted_aes_key_b64: Base64 encoded AES key encrypted with public key
            initial_vector_b64: Base64 encoded initialization vector

        Returns:
            Decrypted data as dictionary
        """
        cls._load_keys()

        # Decode from base64
        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        encrypted_flow_data = base64.b64decode(encrypted_flow_data_b64)
        initial_vector = base64.b64decode(initial_vector_b64)

        # Decrypt AES key using private key
        aes_key = cls._private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Decrypt data using AES key
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(initial_vector),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        # Split tag from data (last 16 bytes)
        encrypted_flow_data_body = encrypted_flow_data[:-16]
        tag = encrypted_flow_data[-16:]

        # Decrypt
        decrypted_data = decryptor.update(encrypted_flow_data_body) + decryptor.finalize_with_tag(tag)

        # Parse JSON
        return json.loads(decrypted_data.decode('utf-8'))

    @classmethod
    def encrypt_response(cls, response_data: Dict[str, Any], aes_key_b64: str, initial_vector_b64: str) -> str:
        """
        Encrypt a response for WhatsApp Flow.

        Args:
            response_data: Response data to encrypt
            aes_key_b64: Base64 encoded AES key from request
            initial_vector_b64: Base64 encoded IV from request

        Returns:
            Base64 encoded encrypted response
        """
        # Decode AES key and IV
        aes_key = base64.b64decode(aes_key_b64)
        initial_vector = base64.b64decode(initial_vector_b64)

        # Flip the IV
        flipped_iv = bytearray(initial_vector)
        flipped_iv[-1] ^= 0xFF
        flipped_iv = bytes(flipped_iv)

        # Encrypt response
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(flipped_iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Serialize to JSON
        json_data = json.dumps(response_data).encode('utf-8')

        # Encrypt
        encrypted_data = encryptor.update(json_data) + encryptor.finalize()
        encrypted_data_with_tag = encrypted_data + encryptor.tag

        # Return base64 encoded
        return base64.b64encode(encrypted_data_with_tag).decode('utf-8')

    @classmethod
    def sign_response(cls, response_data: str) -> str:
        """
        Sign the response data with private key.

        Args:
            response_data: The encrypted response data to sign

        Returns:
            Base64 encoded signature
        """
        cls._load_keys()

        signature = cls._private_key.sign(
            response_data.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return base64.b64encode(signature).decode('utf-8')

    @classmethod
    def verify_signature(cls, data: str, signature_b64: str) -> bool:
        """
        Verify signature of incoming data.

        Args:
            data: The data that was signed
            signature_b64: Base64 encoded signature

        Returns:
            True if signature is valid
        """
        cls._load_keys()

        try:
            signature = base64.b64decode(signature_b64)
            cls._public_key.verify(
                signature,
                data.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


def get_private_key_instructions():
    """Get instructions for generating a private key."""
    return """
To generate a private key for WhatsApp Flows:

1. Generate the key:
   openssl genrsa -out private.key 2048

2. View the key:
   cat private.key

3. For Render deployment, encode it for environment variable:

   Option A - Copy as-is and replace newlines:
   - Copy the entire key including BEGIN/END lines
   - In Render environment variable, replace actual newlines with \\n

   Option B - Base64 encode:
   cat private.key | base64 -w 0
   - Copy the output and paste directly into WHATSAPP_FLOW_PRIVATE_KEY

4. Set environment variable in Render:
   WHATSAPP_FLOW_PRIVATE_KEY=<your-key-here>

5. Get your public key:
   - Deploy your app
   - Visit: https://your-app.onrender.com/api/webhook/whatsapp-flow/public-key
   - Copy the public key and paste it in WhatsApp Flow configuration
"""
