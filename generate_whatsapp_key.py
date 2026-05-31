#!/usr/bin/env python3
"""
WhatsApp Flow Key Generator

This script generates an RSA key pair for WhatsApp Flow encryption
and provides the private key in a format ready for Render deployment.

Usage:
    python generate_whatsapp_key.py

The script will:
1. Generate a 2048-bit RSA private key
2. Save it to private.key
3. Display the base64-encoded version for Render
4. Show the public key endpoint URL
"""

import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_key_pair():
    """Generate RSA key pair."""
    print("Generating RSA key pair (2048-bit)...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Generate public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem


def main():
    print("=" * 70)
    print("WhatsApp Flow Key Generator for Render Deployment")
    print("=" * 70)
    print()

    # Generate keys
    private_pem, public_pem = generate_key_pair()

    # Save to file
    with open('private.key', 'wb') as f:
        f.write(private_pem)
    print("✓ Private key saved to: private.key")
    print()

    # Base64 encode for Render
    private_b64 = base64.b64encode(private_pem).decode('utf-8')

    print("=" * 70)
    print("STEP 1: Copy this value for Render Environment Variable")
    print("=" * 70)
    print()
    print("Variable Name: WHATSAPP_FLOW_PRIVATE_KEY")
    print()
    print("Variable Value:")
    print("-" * 70)
    print(private_b64)
    print("-" * 70)
    print()

    print("=" * 70)
    print("STEP 2: Deploy to Render")
    print("=" * 70)
    print()
    print("1. Go to your Render dashboard")
    print("2. Select your web service")
    print("3. Go to 'Environment' tab")
    print("4. Add new environment variable:")
    print("   - Key: WHATSAPP_FLOW_PRIVATE_KEY")
    print("   - Value: (paste the value from above)")
    print("5. Save changes (Render will auto-deploy)")
    print()

    print("=" * 70)
    print("STEP 3: Get Your Public Key")
    print("=" * 70)
    print()
    print("After deployment, visit:")
    print("https://your-app.onrender.com/api/webhook/whatsapp-flow/public-key")
    print()
    print("Copy the public key and paste it in WhatsApp Flow settings.")
    print()

    print("=" * 70)
    print("Preview of Public Key:")
    print("=" * 70)
    print(public_pem.decode('utf-8'))

    print("=" * 70)
    print("SECURITY REMINDER")
    print("=" * 70)
    print()
    print("⚠️  NEVER commit private.key to git!")
    print("⚠️  Keep your private key secure")
    print("⚠️  Use different keys for dev/staging/production")
    print()
    print("✓ private.key is already in .gitignore")
    print()

    # Create .gitignore entry if not exists
    try:
        with open('.gitignore', 'r') as f:
            content = f.read()
            if 'private.key' not in content:
                with open('.gitignore', 'a') as f:
                    f.write('\n# WhatsApp Flow private key\nprivate.key\n')
                print("✓ Added private.key to .gitignore")
    except FileNotFoundError:
        with open('.gitignore', 'w') as f:
            f.write('# WhatsApp Flow private key\nprivate.key\n')
        print("✓ Created .gitignore with private.key")

    print()
    print("=" * 70)
    print("Setup complete! Follow the steps above to deploy.")
    print("=" * 70)


if __name__ == '__main__':
    main()
