"""
WhatsApp webhook service for Green API.
Handles webhook setup and incoming webhook events.
"""
import requests
from typing import Dict
from config import Config


class WhatsAppWebhook:
    """Service for managing Green API webhooks"""
    
    def __init__(self):
        self.base_url = Config.GREEN_API_BASE_URL
        self.token = Config.GREEN_API_TOKEN
        self.instance_id = Config.GREEN_API_INSTANCE_ID
        
        if not Config.validate_green_api_config():
            raise ValueError("Green API credentials not properly configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Content-Type': 'application/json'
        }
    
    def _get_url(self, endpoint: str) -> str:
        """Build full API URL"""
        return f"{self.base_url}/{endpoint}"
    
    def set_webhook_url(self, webhook_url: str, webhook_token: str = None) -> Dict:
        """
        Set webhook URL for receiving notifications
        
        Args:
            webhook_url: The URL where webhooks will be sent (e.g., https://your-app.railway.app/webhook)
            webhook_token: Optional security token for webhook validation
            
        Returns:
            dict: API response
                - success (bool): Whether the operation was successful
                - data (dict): Response data if successful
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/SetSettings/{self.token}")
        
        payload = {
            "webhookUrl": webhook_url,
            "webhookUrlToken": webhook_token or Config.WEBHOOK_TOKEN,
            "markIncomingMessagesReaded": "yes",
            "incomingWebhook": "yes",
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=10)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            print(f"Error setting webhook URL: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_webhook_settings(self) -> Dict:
        """
        Get current webhook settings
        
        Returns:
            dict: Webhook settings response
                - success (bool): Whether the operation was successful
                - settings (dict): Webhook settings if successful
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/GetSettings/{self.token}")
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return {
                'success': True,
                'settings': response.json()
            }
        except requests.exceptions.RequestException as e:
            print(f"Error getting webhook settings: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_webhook_url(self) -> Dict:
        """
        Delete webhook URL (disable webhooks)
        
        Returns:
            dict: API response
                - success (bool): Whether the operation was successful
                - data (dict): Response data if successful
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/SetSettings/{self.token}")
        
        payload = {
            "webhookUrl": "",
            "incomingWebhook": "no"
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=10)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            print(f"Error deleting webhook URL: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_webhook_token(self, provided_token: str) -> bool:
        """
        Verify webhook token for security
        
        Args:
            provided_token: Token provided in webhook request
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        return provided_token == Config.WEBHOOK_TOKEN
    
    def setup_webhook_for_railway(self, railway_url: str) -> Dict:
        """
        Helper method to set up webhook for Railway deployment
        
        Args:
            railway_url: Your Railway app URL (e.g., https://your-app.railway.app)
            
        Returns:
            dict: Setup result
                - success (bool): Whether setup was successful
                - webhook_url (str): The configured webhook URL
                - error (str): Error message if failed
        """
        webhook_url = f"{railway_url.rstrip('/')}/webhook"
        
        result = self.set_webhook_url(webhook_url)
        
        if result['success']:
            return {
                'success': True,
                'webhook_url': webhook_url,
                'message': f'Webhook configured successfully for {webhook_url}'
            }
        else:
            return {
                'success': False,
                'error': result.get('error'),
                'message': 'Failed to configure webhook'
            }


# Singleton instance
_webhook_service = None

def get_webhook_service() -> WhatsAppWebhook:
    """Get or create webhook service singleton"""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WhatsAppWebhook()
    return _webhook_service
