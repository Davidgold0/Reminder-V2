"""
Tools for the AI agent to interact with the reminder system.
These tools give the agent capabilities to manage users, events, and messages.
"""
from langchain.tools import tool
from typing import Optional
from datetime import datetime
import json
import logging

# Set up global logger for agent tools
logger = logging.getLogger(__name__)


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
    IMPORTANT: User must be fully registered before creating reminders.
    
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
    logger.info(f"create_reminder called for user_phone={user_phone}, is_recurring={is_recurring}")
    logger.debug(f"Reminder details: description='{description}', event_time='{event_time}', "
                 f"recurrence_frequency={recurrence_frequency}, recurrence_days_of_week={recurrence_days_of_week}")
    
    try:
        from services.db.users import get_user_by_phone
        from services.db.events import add_event
        
        # Check if user exists and is registered
        logger.debug(f"Fetching user by phone: {user_phone}")
        user_result = get_user_by_phone(user_phone)
        if not user_result['success']:
            logger.warning(f"User not found: {user_phone}")
            return "Error: User not found. Please complete registration first by providing your name, language, and timezone."
        
        user = user_result['user']
        logger.debug(f"User found: id={user.get('id')}, is_registered={user.get('is_registered')}")
        
        # Check if user is fully registered
        if not user.get('is_registered'):
            logger.warning(f"User {user_phone} attempted to create reminder but is not fully registered")
            return "❌ You need to complete registration before creating reminders. Please provide your full name, preferred language, and timezone first."
        
        user_id = user_result['user']['id']
        
        # Parse event time
        try:
            event_datetime = datetime.fromisoformat(event_time)
            logger.debug(f"Parsed event_time: {event_datetime}")
        except ValueError as ve:
            logger.error(f"Invalid date/time format for event_time '{event_time}': {ve}")
            return f"Error: Invalid date/time format. Use YYYY-MM-DD HH:MM:SS"
        
        # Create the event
        logger.debug(f"Creating event for user_id={user_id}")
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
            logger.info(f"Successfully created {'recurring' if is_recurring else 'one-time'} reminder: "
                       f"event_id={event.get('id')}, description='{description}'")
            if is_recurring:
                return f"✓ Recurring reminder created: '{description}' starting {event_time}, repeating {recurrence_frequency}"
            else:
                return f"✓ Reminder created: '{description}' scheduled for {event_time}"
        else:
            logger.error(f"Failed to create event: {event_result['error']}")
            return f"Error: {event_result['error']}"
            
    except Exception as e:
        logger.exception(f"Exception in create_reminder for user {user_phone}: {str(e)}")
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
    logger.info(f"get_user_reminders called for user_phone={user_phone}, limit={limit}")
    
    try:
        from services.db.users import get_user_by_phone
        from services.db.events import get_upcoming_events
        
        # Get user
        logger.debug(f"Fetching user by phone: {user_phone}")
        user_result = get_user_by_phone(user_phone)
        if not user_result['success']:
            logger.warning(f"User not found when retrieving reminders: {user_phone}")
            return "No reminders found. You haven't created any reminders yet."
        
        user_id = user_result['user']['id']
        logger.debug(f"User found: user_id={user_id}")
        
        # Get upcoming events
        events_result = get_upcoming_events(user_id=user_id, limit=limit)
        
        if not events_result['success']:
            logger.error(f"Error retrieving upcoming events for user_id={user_id}: {events_result['error']}")
            return f"Error: {events_result['error']}"
        
        if events_result['count'] == 0:
            logger.info(f"No upcoming reminders found for user_id={user_id}")
            return "You have no upcoming reminders."
        
        logger.info(f"Retrieved {events_result['count']} reminder(s) for user_id={user_id}")
        
        # Format reminders
        reminders_text = f"You have {events_result['count']} upcoming reminder(s):\n\n"
        for i, event in enumerate(events_result['events'], 1):
            event_time = datetime.fromisoformat(event['event_time'])
            reminders_text += f"{i}. {event['description']}\n   📅 {event_time.strftime('%Y-%m-%d %H:%M')}\n"
            if event['is_recurring']:
                reminders_text += f"   🔁 Repeats {event['recurrence_frequency']}\n"
            reminders_text += "\n"
        
        logger.debug(f"Formatted reminders response for user_id={user_id}")
        return reminders_text
        
    except Exception as e:
        logger.exception(f"Exception in get_user_reminders for user {user_phone}: {str(e)}")
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
    Complete user registration by updating their profile with full information.
    The user already exists in the system (created on first message), this tool completes their registration.
    
    IMPORTANT: You MUST collect and provide ALL fields:
    - first_name (required)
    - last_name (required)
    - language (required, e.g., 'en', 'es', 'fr', 'he')
    - timezone (required, e.g., 'America/New_York', 'Europe/London', 'Asia/Jerusalem', 'UTC')
    
    Args:
        phone: User's phone number
        first_name: User's first name (REQUIRED)
        last_name: User's last name (REQUIRED)
        language: User's preferred language code (REQUIRED)
        timezone: User's timezone (REQUIRED, e.g., 'America/New_York')
    
    Returns:
        Registration status message
    """
    logger.info(f"get_or_create_user called for phone={phone}, first_name={first_name}, last_name={last_name}")
    logger.debug(f"Registration details: language={language}, timezone={timezone}")
    
    try:
        from services.db.users import get_user_by_phone, update_user
        
        # Get user (should always exist now)
        logger.debug(f"Fetching user by phone: {phone}")
        result = get_user_by_phone(phone)
        
        if not result['success']:
            logger.error(f"User not found during registration: {phone}")
            return "Error: User not found. Please contact support."
        
        user = result['user']
        logger.debug(f"User found: user_id={user.get('id')}, is_registered={user.get('is_registered')}")
        
        # Check if already registered
        if user.get('is_registered'):
            logger.info(f"User {phone} already registered: {user['first_name']} {user['last_name']}")
            return f"User already registered: {user['first_name']} {user['last_name']} (Language: {user['language']}, Timezone: {user['timezone']})"
        
        # Update user with full registration info
        logger.debug(f"Updating user {phone} with registration details")
        update_result = update_user(
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
            language=language,
            timezone=timezone
        )
        
        if update_result['success']:
            user = update_result['user']
            if user['is_registered']:
                logger.info(f"Successfully registered user: phone={phone}, name={first_name} {last_name}")
                return f"✅ Registration complete! Welcome {first_name} {last_name}! You can now create reminders. (Language: {language}, Timezone: {timezone})"
            else:
                logger.warning(f"Profile updated for {phone} but user is not fully registered")
                return f"Profile updated but missing some information. Please provide all required details."
        else:
            logger.error(f"Failed to update user {phone}: {update_result['error']}")
            return f"Error: {update_result['error']}"
                
    except Exception as e:
        logger.exception(f"Exception in get_or_create_user for phone {phone}: {str(e)}")
        return f"Error with user registration: {str(e)}"


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
    logger.info(f"send_whatsapp_message called for phone={phone}")
    logger.debug(f"Message content (first 100 chars): {message[:100]}...")
    
    try:
        from services.messages.whatsapp_client import get_whatsapp_client
        
        logger.debug("Getting WhatsApp client")
        client = get_whatsapp_client()
        result = client.send_message(phone=phone, message=message)
        
        if result['success']:
            logger.info(f"Successfully sent WhatsApp message to {phone}")
            return f"✓ Message sent successfully to {phone}"
        else:
            logger.error(f"Failed to send WhatsApp message to {phone}: {result['error']}")
            return f"Error sending message: {result['error']}"
            
    except Exception as e:
        logger.exception(f"Exception in send_whatsapp_message for phone {phone}: {str(e)}")
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
    logger.info(f"confirm_reminder called for event_id={event_id}")
    
    try:
        from services.db.events import confirm_event
        
        logger.debug(f"Confirming event: event_id={event_id}")
        result = confirm_event(event_id)
        
        if result['success']:
            logger.info(f"Successfully confirmed event: event_id={event_id}")
            return f"✓ {result['message']}"
        else:
            logger.error(f"Failed to confirm event {event_id}: {result['error']}")
            return f"Error: {result['error']}"
            
    except Exception as e:
        logger.exception(f"Exception in confirm_reminder for event_id {event_id}: {str(e)}")
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
    logger.info(f"get_last_messages called for user_id={user_id}, n={n}")
    
    try:
        from services.db.messages import get_last_n_messages
        
        logger.debug(f"Fetching last {n} messages for user_id={user_id}")
        result = get_last_n_messages(user_id, n)
        
        if not result['success']:
            logger.error(f"Error retrieving messages for user_id={user_id}: {result['error']}")
            return f"Error: {result['error']}"
        
        messages = result['messages']
        
        if not messages:
            logger.info(f"No message history found for user_id={user_id}")
            return "No message history found."
        
        logger.info(f"Retrieved {len(messages)} messages for user_id={user_id}")
        
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
        
        logger.debug(f"Formatted {len(messages)} messages for user_id={user_id}")
        return formatted
            
    except Exception as e:
        logger.exception(f"Exception in get_last_messages for user_id {user_id}: {str(e)}")
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
    logger.info(f"get_upcoming_reminders called for user_id={user_id}, limit={limit}")
    
    try:
        from services.db.events import get_upcoming_events
        from datetime import datetime
        
        logger.debug(f"Fetching upcoming events for user_id={user_id}")
        result = get_upcoming_events(user_id, limit=limit)
        
        if not result['success']:
            logger.error(f"Error retrieving upcoming events for user_id={user_id}: {result['error']}")
            return f"Error: {result['error']}"
        
        events = result['events']
        
        if not events:
            logger.info(f"No upcoming reminders found for user_id={user_id}")
            return "📅 No upcoming reminders found."
        
        logger.info(f"Retrieved {len(events)} upcoming reminder(s) for user_id={user_id}")
        
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
        
        logger.debug(f"Formatted {len(events)} upcoming reminders for user_id={user_id}")
        return formatted
            
    except Exception as e:
        logger.exception(f"Exception in get_upcoming_reminders for user_id {user_id}: {str(e)}")
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
