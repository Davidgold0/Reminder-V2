#!/usr/bin/env python3
"""
Standalone script to set up WhatsApp webhook with Green API.
This script reads configuration from .env file and sets up the webhook.

Usage:
    python setup_webhook.py
    
Required environment variables in .env:
    - GREEN_API_INSTANCE_ID: Your Green API instance ID
    - GREEN_API_TOKEN: Your Green API token
    - WEBHOOK_URL: Your webhook URL (e.g., https://your-app.railway.app/webhook)
    - WEBHOOK_TOKEN: (Optional) Security token for webhook validation
"""
import os
import sys
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()


def validate_config():
    """Validate that required environment variables are set"""
    required_vars = {
        'GREEN_API_INSTANCE_ID': os.environ.get('GREEN_API_INSTANCE_ID'),
        'GREEN_API_TOKEN': os.environ.get('GREEN_API_TOKEN'),
        'WEBHOOK_URL': os.environ.get('WEBHOOK_URL'),
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file")
        return False
    
    return True


def setup_webhook():
    """Set up the WhatsApp webhook with Green API"""
    
    # Get configuration from environment
    base_url = os.environ.get('GREEN_API_BASE_URL', 'https://api.green-api.com')
    instance_id = os.environ.get('GREEN_API_INSTANCE_ID')
    token = os.environ.get('GREEN_API_TOKEN')
    webhook_url = os.environ.get('WEBHOOK_URL')
    webhook_token = os.environ.get('WEBHOOK_TOKEN', 'default_webhook_token')
    
    # Build API URL
    api_url = f"{base_url}/waInstance{instance_id}/SetSettings/{token}"
    
    # Prepare payload
    payload = {
        "webhookUrl": webhook_url,
        "webhookUrlToken": webhook_token,
        "markIncomingMessagesReaded": "yes",
        "incomingWebhook": "yes",
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print("🔧 Setting up WhatsApp webhook...")
    print(f"   Instance ID: {instance_id}")
    print(f"   Webhook URL: {webhook_url}")
    print(f"   Webhook Token: {'*' * len(webhook_token)}")
    print()
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        print("✅ Webhook configured successfully!")
        print(f"   Response: {result}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error setting webhook: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text}")
        return False


def get_current_settings():
    """Get and display current webhook settings"""
    
    base_url = os.environ.get('GREEN_API_BASE_URL', 'https://api.green-api.com')
    instance_id = os.environ.get('GREEN_API_INSTANCE_ID')
    token = os.environ.get('GREEN_API_TOKEN')
    
    api_url = f"{base_url}/waInstance{instance_id}/GetSettings/{token}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print("\n📋 Fetching current webhook settings...")
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        settings = response.json()
        print("✅ Current settings:")
        print(f"   Webhook URL: {settings.get('webhookUrl', 'Not set')}")
        print(f"   Incoming Webhook: {settings.get('incomingWebhook', 'Not set')}")
        print(f"   Mark Messages Read: {settings.get('markIncomingMessagesReaded', 'Not set')}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching settings: {e}")
        return False


def main():
    """Main function"""
    print("=" * 60)
    print("WhatsApp Webhook Setup Script")
    print("=" * 60)
    print()
    
    # Validate configuration
    if not validate_config():
        sys.exit(1)
    
    # Set up webhook
    success = setup_webhook()
    
    if not success:
        sys.exit(1)
    
    # Get current settings to verify
    get_current_settings()
    
    print()
    print("=" * 60)
    print("Setup complete! Your webhook is now configured.")
    print("=" * 60)


if __name__ == '__main__':
    main()
