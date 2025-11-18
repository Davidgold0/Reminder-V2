"""
Webhook handler for incoming WhatsApp messages.
Processes webhooks from Green API.
"""
from flask import request, jsonify
from services.messages.whatsapp_client import get_whatsapp_client
from config import Config


def handle_webhook():
    """
    Handle incoming WhatsApp webhook from Green API.
    Processes incoming messages and triggers appropriate actions.
    
    Returns:
        tuple: JSON response and HTTP status code
    """
    try:
        # Get the webhook data
        data = request.get_json()
        
        # Optional: Verify webhook token for security
        # webhook_token = request.headers.get('X-Webhook-Token')
        # if webhook_token != Config.WEBHOOK_TOKEN:
        #     return jsonify({'error': 'Invalid webhook token'}), 401
        
        print(f"Received webhook: {data}")
        
        # Parse the incoming message
        client = get_whatsapp_client()
        message_data = client.parse_incoming_message(data)
        
        print(f"Parsed message data: {message_data}")
        
        if message_data:
            phone = message_data['phone']
            message_text = message_data['message']
            
            print(f"Message from {phone}: {message_text}")
            
            # Process the message with the agent
            response = process_incoming_message(phone, message_text)
            
            # Send response back via WhatsApp
            if response.get('success') and response.get('reply'):
                client.send_message(phone=phone, message=response['reply'])
            
            return jsonify({
                'success': True,
                'message': 'Webhook received and processed'
            }), 200
        else:
            # Not a text message or couldn't parse
            return jsonify({
                'success': True,
                'message': 'Webhook received but not a text message'
            }), 200
            
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def process_incoming_message(phone: str, message_text: str) -> dict:
    """
    Process an incoming message from a user.
    Checks if user exists, saves message to DB, and gets AI response.
    
    Args:
        phone: Phone number of the sender
        message_text: The message text
        
    Returns:
        dict: Processing result with success status and reply
    """
    try:
        from services.db.users import get_user_by_phone
        from services.db.messages import add_message
        from services.agent import get_agent
        from services.agent_tools import AGENT_TOOLS
        
        # Check if user exists
        user_result = get_user_by_phone(phone)
        
        user_id = None
        user_full_name = None
        user_language = "en"
        user_timezone = "UTC"
        
        if user_result['success']:
            # Existing user - get their info
            user = user_result['user']
            user_id = user['id']
            user_full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            user_language = user.get('language', 'en')
            user_timezone = user.get('timezone', 'UTC')
            
            # Save incoming message to database
            add_message(
                user_id=user_id,
                sent_by='user',
                message_text=message_text,
                required_follow_up=False
            )
        
        # Get agent and process message
        agent = get_agent(tools=AGENT_TOOLS)
        response_text = agent.process_message(
            phone=phone,
            message=message_text,
            user_id=user_id,
            user_full_name=user_full_name,
            user_language=user_language,
            user_timezone=user_timezone
        )
        
        # Save AI response to database if user exists
        if user_id:
            add_message(
                user_id=user_id,
                sent_by='ai',
                message_text=response_text,
                required_follow_up=False
            )
        
        return {
            'success': True,
            'processed': True,
            'reply': response_text
        }
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return {
            'success': False,
            'error': str(e),
            'reply': "I apologize, but I encountered an error. Please try again."
        }
