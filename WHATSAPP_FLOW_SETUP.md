# WhatsApp Flow Setup Guide

This guide will help you set up WhatsApp Flows with encryption and signing for your Foodie Robot backend, optimized for easy deployment on Render or similar platforms.

## What's Implemented

Your backend now supports:
- RSA encryption/decryption for WhatsApp Flow messages
- Request signature verification
- Response signing
- Automatic public key generation from private key
- Simple environment variable configuration

## Quick Setup (5 minutes)

### Step 1: Generate Private Key

On your local machine, run:

```bash
openssl genrsa -out private.key 2048
```

### Step 2: Prepare for Deployment

You have two options to set up your private key:

#### Option A: Base64 Encode (Recommended for Render)

```bash
# On Linux/Mac:
cat private.key | base64 -w 0

# On Windows (PowerShell):
[Convert]::ToBase64String([IO.File]::ReadAllBytes("private.key"))
```

Copy the entire output (it will be one long line).

#### Option B: Use Raw Key with Escaped Newlines

Copy the entire content of `private.key` including the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines. When pasting into Render, replace actual newlines with `\n`.

### Step 3: Deploy to Render

1. Go to your Render dashboard
2. Navigate to your web service
3. Go to "Environment" section
4. Add a new environment variable:
   - Key: `WHATSAPP_FLOW_PRIVATE_KEY`
   - Value: Paste the base64 string from Step 2
5. Save changes (Render will automatically redeploy)

### Step 4: Get Your Public Key

Once deployed, visit:
```
https://your-app.onrender.com/api/webhook/whatsapp-flow/public-key
```

Copy the entire public key (including the BEGIN/END lines).

### Step 5: Configure WhatsApp Flow

1. Go to Meta Developer Console
2. Navigate to your WhatsApp Flow
3. In the "Endpoint" section:
   - Endpoint URL: `https://your-app.onrender.com/api/webhook/whatsapp-flow`
   - Public Key: Paste the key from Step 4
4. Save and publish your flow

## Testing

### Test Public Key Endpoint

```bash
curl https://your-app.onrender.com/api/webhook/whatsapp-flow/public-key
```

You should see a PEM-formatted public key.

### Test Flow Webhook

Send a test flow from WhatsApp. Check your Render logs to see:
- Raw encrypted request
- Decrypted flow data
- Response being sent

## Customizing Your Flow Logic

The flow logic is in `api/views/whatsapp_flow_webhook.py` in the `process_flow_data()` function.

### Example: Handle Different Screens

```python
def process_flow_data(decrypted_data: dict) -> dict:
    version = decrypted_data.get('version')
    screen = decrypted_data.get('screen')
    data = decrypted_data.get('data', {})
    action = decrypted_data.get('action')

    if action == 'INIT':
        # First screen when flow opens
        return {
            'version': version,
            'screen': 'WELCOME',
            'data': {
                'restaurant_name': 'Foodie Robot',
                'greeting': 'Welcome! Choose an option:'
            }
        }

    if action == 'data_exchange':
        if screen == 'WELCOME':
            # User selected something on welcome screen
            choice = data.get('user_choice')

            if choice == 'view_menu':
                return {
                    'version': version,
                    'screen': 'MENU',
                    'data': {
                        'items': ['Pizza', 'Burger', 'Salad']
                    }
                }

        if screen == 'MENU':
            # User selected menu item
            selected_item = data.get('item')

            return {
                'version': version,
                'screen': 'CONFIRM',
                'data': {
                    'item': selected_item,
                    'price': get_price(selected_item)
                }
            }

    return {
        'version': version,
        'data': {'status': 'received'}
    }
```

## Environment Variables Reference

Required:
- `WHATSAPP_FLOW_PRIVATE_KEY` - Your RSA private key (base64 encoded or with escaped newlines)

Existing (already configured):
- `SECRET_KEY` - Django secret key
- `WHATSAPP_MESSAGE_BASE_URL` - WhatsApp API base URL
- `WHATSAPP_API_KEY` - WhatsApp API key
- `WHATSAPP_API_VERIFY_TOKEN` - Webhook verification token
- `DATABASE_*` - Database configuration

## Security Notes

1. **Never commit private keys to git** - Always use environment variables
2. **Use different keys for dev/production** - Generate separate keys for each environment
3. **Rotate keys periodically** - Generate new keys every 6-12 months
4. **Monitor webhook logs** - Watch for unusual activity

## Troubleshooting

### "No WHATSAPP_FLOW_PRIVATE_KEY found"

**Solution**: Make sure you set the environment variable in Render. Check the spelling and that there are no extra spaces.

### "Error generating public key"

**Solution**: Your private key format might be incorrect. Try:
1. Regenerate the key with `openssl genrsa -out private.key 2048`
2. Use base64 encoding (Option A in Step 2)
3. Check Render logs for specific error messages

### "Signature verification failed"

**Solution**:
- Make sure the public key in WhatsApp Flow settings matches your deployed key
- Regenerate and redeploy if you recently changed the private key

### "Decryption failed"

**Solution**:
- Ensure your endpoint URL in WhatsApp Flow settings is correct
- Check that the request is actually coming from WhatsApp
- Look at Render logs for detailed error messages

## Local Development

For local development, you can use the same private key:

1. Create a `.env` file (already in .gitignore):
   ```
   WHATSAPP_FLOW_PRIVATE_KEY=<your-base64-key>
   ```

2. Run locally:
   ```bash
   python manage.py runserver
   ```

3. Use ngrok to expose your local server:
   ```bash
   ngrok http 8000
   ```

4. Use the ngrok URL in WhatsApp Flow settings (remember to update the public key endpoint URL too)

## Architecture

```
WhatsApp → Encrypted Request → Your Endpoint
                                     ↓
                              Decrypt with private key
                                     ↓
                              Process business logic
                                     ↓
                              Encrypt with AES key
                                     ↓
                              Sign with private key
                                     ↓
                              Return to WhatsApp
```

## Files Modified/Created

- `api/utils/whatsapp_flow_crypto.py` - Encryption/decryption utilities
- `api/views/whatsapp_flow_webhook.py` - Webhook handlers
- `requirements.txt` - Added cryptography package
- `WHATSAPP_FLOW_SETUP.md` - This guide

## Need Help?

Check the logs in Render for detailed error messages. The webhook prints:
- Raw encrypted requests
- Decrypted data
- Processing steps
- Errors with full stack traces

## Next Steps

1. Test your flow end-to-end
2. Implement your specific flow logic in `process_flow_data()`
3. Add database integration if needed
4. Set up monitoring for webhook failures
5. Create additional flow screens in Meta Developer Console

## Performance Notes

This implementation is designed for platforms like Render:
- Keys are loaded once and cached
- No file system dependencies (everything in env vars)
- Minimal memory footprint
- Automatic error recovery
- Detailed logging for debugging
