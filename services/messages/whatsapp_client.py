"""
WhatsApp messaging service using Green API.
Handles sending and receiving WhatsApp messages.
"""
import requests
from typing import Dict, List, Optional
from config import Config


class WhatsAppClient:
    """Client for interacting with Green API WhatsApp service"""
    
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
    
    def send_message(self, phone: str, message: str) -> Dict:
        """
        Send a WhatsApp message using Green API
        
        Args:
            phone: Phone number with country code (no + or spaces, e.g., "1234567890")
            message: Message text to send
            
        Returns:
            dict: API response with success status
                - success (bool): Whether the operation was successful
                - data (dict): Response data if successful
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/SendMessage/{self.token}")
        
        # Clean phone number (remove + and spaces)
        clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        payload = {
            "chatId": f"{clean_phone}@c.us",
            "message": message
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=10)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_notifications(self) -> Dict:
        """
        Get incoming notifications/messages using Green API
        
        Returns:
            dict: Notifications response
                - success (bool): Whether the operation was successful
                - notifications (list): List of notification objects if successful
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/ReceiveNotification/{self.token}")
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'notifications': data if isinstance(data, list) else [data] if data else []
            }
        except requests.exceptions.RequestException as e:
            print(f"Error getting notifications: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_notification(self, receipt_id: int) -> Dict:
        """
        Delete a notification after processing
        
        Args:
            receipt_id: ID of the notification to delete
            
        Returns:
            dict: Deletion response
                - success (bool): Whether the operation was successful
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/DeleteNotification/{self.token}/{receipt_id}")
        
        try:
            response = requests.delete(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return {
                'success': True
            }
        except requests.exceptions.RequestException as e:
            print(f"Error deleting notification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_state_instance(self) -> Dict:
        """
        Get the current state of the WhatsApp instance
        
        Returns:
            dict: Instance state response
                - success (bool): Whether the operation was successful
                - state (str): Instance state if successful
                - data (dict): Full response data
                - error (str): Error message if failed
        """
        url = self._get_url(f"waInstance{self.instance_id}/getStateInstance/{self.token}")
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                'success': True,
                'state': data.get('stateInstance'),
                'data': data
            }
        except requests.exceptions.RequestException as e:
            print(f"Error getting instance state: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_instance_authorized(self) -> bool:
        """
        Check if the WhatsApp instance is authorized and ready
        
        Returns:
            bool: True if authorized, False otherwise
        """
        try:
            result = self.get_state_instance()
            return result.get('success') and result.get('state') == 'authorized'
        except Exception as e:
            print(f"Error checking instance authorization: {e}")
            return False
    
    def parse_incoming_message(self, notification: Dict) -> Optional[Dict]:
        """
        Parse an incoming notification to extract message details
        
        Args:
            notification: Notification object from Green API (can be webhook or API notification)
            
        Returns:
            dict: Parsed message data or None if not a text message
                - phone (str): Sender's phone number
                - message (str): Message text
                - timestamp (int): Message timestamp
                - receipt_id (int): Notification receipt ID
        """
        try:
            # Handle webhook format (direct structure) vs API notification format (wrapped in 'body')
            webhook_data = notification.get('body') if 'body' in notification else notification
            
            if webhook_data.get('typeWebhook') == 'incomingMessageReceived':
                message_data = webhook_data.get('messageData', {})
                
                # Extract phone number (remove @c.us)
                sender = webhook_data.get('senderData', {}).get('sender', '')
                phone = sender.replace('@c.us', '')
                
                # Only process text messages
                if message_data.get('typeMessage') == 'textMessage':
                    return {
                        'phone': phone,
                        'message': message_data.get('textMessageData', {}).get('textMessage', ''),
                        'timestamp': webhook_data.get('timestamp'),
                        'receipt_id': notification.get('receiptId')
                    }
            
            return None
        except Exception as e:
            print(f"Error parsing incoming message: {e}")
            return None


# Singleton instance
_whatsapp_client = None

def get_whatsapp_client() -> WhatsAppClient:
    """Get or create WhatsApp client singleton"""
    global _whatsapp_client
    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()
    return _whatsapp_client
