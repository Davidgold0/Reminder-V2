"""
Utility functions for the AI agent.
Helper functions for conversation management and context building.
"""
from typing import List, Dict, Optional


def build_conversation_history(user_id: Optional[int], current_message: str, n: int = 10) -> List[Dict[str, str]]:
    """
    Build conversation history from database messages.
    
    Args:
        user_id: User's ID (None for new users)
        current_message: The current message from the user
        n: Number of previous messages to retrieve (default: 10)
    
    Returns:
        List of message dictionaries with role and content
    """
    conversation_history = []
    
    # Get previous messages if user exists
    if user_id:
        from services.db.messages import get_last_n_messages
        result = get_last_n_messages(user_id, n=n)
        
        if result['success'] and result['messages']:
            # Format messages for the agent (reverse to get chronological order)
            for msg in reversed(result['messages']):
                role = "assistant" if msg['sent_by'] == 'ai' else "user"
                message_content = msg['message_text']
                
                # If message is connected to an event, add event ID to content
                if msg.get('event_id'):
                    message_content = f"[Event ID: {msg['event_id']}] {message_content}"
                
                conversation_history.append({
                    "role": role,
                    "content": message_content
                })
    
    # Add current message
    conversation_history.append({"role": "user", "content": current_message})
    
    return conversation_history
