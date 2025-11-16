"""
Tools for the AI agent to interact with the reminder system.
These tools give the agent capabilities to manage users, events, and messages.
"""
from langchain.tools import tool
from typing import Optional
from datetime import datetime
import json


@tool
def create_reminder(
    user_phone: str,
    description: str,
    event_time: str,
    is_recurring: bool = False,
    recurrence_frequency: Optional[str] = None,
    recurrence_days_of_week: Optional[str] = None
) -> str:
    """
    Create a reminder/event for a user. Supports BOTH one-time and recurring events.
    
    ONE-TIME EVENTS: Just set description and event_time
    RECURRING EVENTS: Set is_recurring=True and recurrence_frequency
    
    Args:
        user_phone: User's phone number
        description: What to remind about
        event_time: When to send the reminder (ISO format: YYYY-MM-DD HH:MM:SS)
        is_recurring: Set to True for recurring events (default: False)
        recurrence_frequency: REQUIRED for recurring - 'daily', 'weekly', 'monthly', or 'yearly'
        recurrence_days_of_week: For weekly recurring - which days (e.g., "1,3,5" for Mon,Wed,Fri where 0=Monday, 6=Sunday)
    
    Examples:
        - One-time: create_reminder(phone, "Doctor appointment", "2025-11-20 14:00:00")
        - Daily: create_reminder(phone, "Take medicine", "2025-11-15 09:00:00", True, "daily")
        - Weekly: create_reminder(phone, "Team meeting", "2025-11-18 10:00:00", True, "weekly", "0")  # Every Monday
    
    Returns:
        Success message or error
    """
    try:
        from services.db.users import get_user_by_phone
        from services.db.events import add_event
        
        # Check if user exists - FAIL if they don't
        user_result = get_user_by_phone(user_phone)
        if not user_result['success']:
            return "Error: User not found. Please complete registration first by providing your name, language, and timezone."
        
        user_id = user_result['user']['id']
        
        # Parse event time
        try:
            event_datetime = datetime.fromisoformat(event_time)
        except ValueError:
            return f"Error: Invalid date/time format. Use YYYY-MM-DD HH:MM:SS"
        
        # Create the event
        event_result = add_event(
            user_id=user_id,
            description=description,
            event_time=event_datetime,
            is_recurring=is_recurring,
            recurrence_frequency=recurrence_frequency if is_recurring else None,
            recurrence_days_of_week=recurrence_days_of_week
        )
        
        if event_result['success']:
            event = event_result['event']
            if is_recurring:
                return f"✓ Recurring reminder created: '{description}' starting {event_time}, repeating {recurrence_frequency}"
            else:
                return f"✓ Reminder created: '{description}' scheduled for {event_time}"
        else:
            return f"Error: {event_result['error']}"
            
    except Exception as e:
        return f"Error creating reminder: {str(e)}"


@tool
def get_user_reminders(user_phone: str, limit: int = 10) -> str:
    """
    Get upcoming reminders for a user.
    
    Args:
        user_phone: User's phone number
        limit: Maximum number of reminders to return
    
    Returns:
        List of upcoming reminders
    """
    try:
        from services.db.users import get_user_by_phone
        from services.db.events import get_upcoming_events
        
        # Get user
        user_result = get_user_by_phone(user_phone)
        if not user_result['success']:
            return "No reminders found. You haven't created any reminders yet."
        
        user_id = user_result['user']['id']
        
        # Get upcoming events
        events_result = get_upcoming_events(user_id=user_id, limit=limit)
        
        if not events_result['success']:
            return f"Error: {events_result['error']}"
        
        if events_result['count'] == 0:
            return "You have no upcoming reminders."
        
        # Format reminders
        reminders_text = f"You have {events_result['count']} upcoming reminder(s):\n\n"
        for i, event in enumerate(events_result['events'], 1):
            event_time = datetime.fromisoformat(event['event_time'])
            reminders_text += f"{i}. {event['description']}\n   📅 {event_time.strftime('%Y-%m-%d %H:%M')}\n"
            if event['is_recurring']:
                reminders_text += f"   🔁 Repeats {event['recurrence_frequency']}\n"
            reminders_text += "\n"
        
        return reminders_text
        
    except Exception as e:
        return f"Error getting reminders: {str(e)}"


@tool
def get_or_create_user(
    phone: str, 
    first_name: str,
    last_name: str,
    language: str = "en",
    timezone: str = "UTC"
) -> str:
    """
    Get user info or create a new user if they don't exist.
    IMPORTANT: When creating a new user, you MUST ask for and provide:
    - first_name (required)
    - last_name (required)
    - language (required, e.g., 'en', 'es', 'fr')
    - timezone (required, e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo')
    
    Args:
        phone: User's phone number
        first_name: User's first name (REQUIRED)
        last_name: User's last name (REQUIRED)
        language: User's preferred language code (REQUIRED)
        timezone: User's timezone (REQUIRED, e.g., 'America/New_York')
    
    Returns:
        User information
    """
    try:
        from services.db.users import get_user_by_phone, add_user
        
        # Try to get user
        result = get_user_by_phone(phone)
        
        if result['success']:
            user = result['user']
            return f"User found: {user['first_name']} {user['last_name']} (Language: {user['language']}, Timezone: {user['timezone']})"
        else:
            # Create new user - ALL fields are now required
            create_result = add_user(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                language=language,
                timezone=timezone
            )
            if create_result['success']:
                user = create_result['user']
                return f"✓ New user registered: {user['first_name']} {user['last_name']} (Language: {language}, Timezone: {timezone})"
            else:
                return f"Error: {create_result['error']}"
                
    except Exception as e:
        return f"Error with user: {str(e)}"


@tool
def send_whatsapp_message(phone: str, message: str) -> str:
    """
    Send a WhatsApp message to a user.
    
    Args:
        phone: Recipient's phone number
        message: Message to send
    
    Returns:
        Success or error message
    """
    try:
        from services.messages.whatsapp_client import get_whatsapp_client
        
        client = get_whatsapp_client()
        result = client.send_message(phone=phone, message=message)
        
        if result['success']:
            return f"✓ Message sent successfully to {phone}"
        else:
            return f"Error sending message: {result['error']}"
            
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def confirm_reminder(event_id: int) -> str:
    """
    Confirm a reminder/event by marking it as confirmed in the database.
    Use this when a user responds to reminder messages with confirmations like:
    - "yes", "ok", "confirmed", "I'll be there", "got it", etc.
    
    This updates the is_confirmed field in the database to True.
    
    Args:
        event_id: The ID of the event/reminder to confirm (shown in reminder messages)
    
    Returns:
        Success message or error
    """
    try:
        from services.db.events import confirm_event
        
        result = confirm_event(event_id)
        
        if result['success']:
            return f"✓ {result['message']}"
        else:
            return f"Error: {result['error']}"
            
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_last_messages(user_id: int, n: int = 20) -> str:
    """
    Retrieve the last N messages exchanged with a user.
    Use this tool when you need MORE conversation history beyond the automatic 10 messages provided.
    This is helpful for understanding context from earlier in the conversation.
    
    Args:
        user_id: The user's ID (available in your state)
        n: Number of recent messages to retrieve (default: 20, can go higher if needed)
    
    Returns:
        Formatted list of recent messages with timestamps or error
    """
    try:
        from services.db.messages import get_last_n_messages
        
        result = get_last_n_messages(user_id, n)
        
        if not result['success']:
            return f"Error: {result['error']}"
        
        messages = result['messages']
        
        if not messages:
            return "No message history found."
        
        # Format messages
        formatted = f"📜 Last {len(messages)} messages:\n\n"
        for msg in messages:
            sender = "🤖 AI" if msg['sent_by'] == 'ai' else "👤 User"
            timestamp = msg['timestamp']
            text = msg['message_text']
            
            # Add event ID if message is connected to an event
            event_info = ""
            if msg.get('event_id'):
                event_info = f"[Event ID: {msg['event_id']}] "
            
            formatted += f"{sender} ({timestamp}):\n{event_info}{text}\n\n"
        
        return formatted
            
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_upcoming_reminders(user_id: int, limit: int = 20) -> str:
    """
    Get upcoming events/reminders for a user.
    Shows events ordered by time, including confirmation status.
    
    Args:
        user_id: The user's ID
        limit: Maximum number of events to retrieve (default: 20)
    
    Returns:
        Formatted list of upcoming events or error
    """
    try:
        from services.db.events import get_upcoming_events
        from datetime import datetime
        
        result = get_upcoming_events(user_id, limit=limit)
        
        if not result['success']:
            return f"Error: {result['error']}"
        
        events = result['events']
        
        if not events:
            return "📅 No upcoming reminders found."
        
        # Format events
        formatted = f"📅 Your upcoming {len(events)} reminder(s):\n\n"
        for i, event in enumerate(events, 1):
            event_time = event['event_time']
            description = event['description']
            event_id = event['id']
            is_confirmed = event.get('is_confirmed', False)
            confirm_status = "✅ Confirmed" if is_confirmed else "⏳ Pending confirmation"
            
            formatted += f"{i}. [{confirm_status}] ID: {event_id}\n"
            formatted += f"   📝 {description}\n"
            formatted += f"   🕐 {event_time}\n\n"
        
        return formatted
            
    except Exception as e:
        return f"Error: {str(e)}"


# List of all tools to pass to the agent
AGENT_TOOLS = [
    create_reminder,
    get_user_reminders,
    get_or_create_user,
    send_whatsapp_message,
    confirm_reminder,
    get_last_messages,
    get_upcoming_reminders
]
