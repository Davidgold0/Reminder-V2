"""
Tools for the AI agent to interact with the reminder system.
These tools give the agent capabilities to manage users, events, and messages.
"""
from langchain.tools import tool, ToolRuntime
from typing import Optional
from datetime import datetime
import json
import logging

# Set up global logger for agent tools
logger = logging.getLogger(__name__)


@tool
def create_reminder(
    description: str,
    event_time: str,
    is_recurring: bool = False,
    recurrence_frequency: Optional[str] = None,
    recurrence_days_of_week: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    Create a reminder/event for a user. Supports BOTH one-time and recurring events.
    IMPORTANT: User must be fully registered before creating reminders.
    
    The user's phone number is automatically retrieved from the agent state - you don't need to provide it.
    
    ONE-TIME EVENTS: Just set description and event_time
    RECURRING EVENTS: Set is_recurring=True and recurrence_frequency
    
    Args:
        description: What to remind about
        event_time: When to send the reminder (ISO format: YYYY-MM-DD HH:MM:SS)
        is_recurring: Set to True for recurring events (default: False)
        recurrence_frequency: REQUIRED for recurring - 'daily', 'weekly', 'monthly', or 'yearly'
        recurrence_days_of_week: For weekly recurring - which days (e.g., "1,3,5" for Mon,Wed,Fri where 0=Monday, 6=Sunday)
    
    Examples:
        - One-time: create_reminder("Doctor appointment", "2025-11-20 14:00:00")
        - Daily: create_reminder("Take medicine", "2025-11-15 09:00:00", True, "daily")
        - Weekly: create_reminder("Team meeting", "2025-11-18 10:00:00", True, "weekly", "0")  # Every Monday
    
    Returns:
        Success message or error
    """
    from services.db.users import get_user_by_phone
    from services.db.events import add_event
    
    # Get phone number from agent state
    user_phone = runtime.state.get("user_phone")
    if not user_phone:
        logger.error("user_phone not found in agent state")
        return "Error: Unable to retrieve user phone number from system."
    
    logger.info(f"create_reminder called for user_phone={user_phone}, is_recurring={is_recurring}")
    logger.debug(f"Reminder details: description='{description}', event_time='{event_time}', "
                 f"recurrence_frequency={recurrence_frequency}, recurrence_days_of_week={recurrence_days_of_week}")
    
    try:
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
def get_user_reminders(limit: int = 10, runtime: ToolRuntime = None) -> str:
    """
    Get upcoming reminders for a user.
    
    The user's phone number is automatically retrieved from the agent state - you don't need to provide it.
    
    Args:
        limit: Maximum number of reminders to return
    
    Returns:
        List of upcoming reminders
    """
    from services.db.users import get_user_by_phone
    from services.db.events import get_upcoming_events
    
    # Get phone number from agent state
    user_phone = runtime.state.get("user_phone")
    if not user_phone:
        logger.error("user_phone not found in agent state")
        return "Error: Unable to retrieve user phone number from system."
    
    logger.info(f"get_user_reminders called for user_phone={user_phone}, limit={limit}")
    
    try:
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
    first_name: str,
    last_name: str,
    language: str = "en",
    timezone: str = "UTC",
    runtime: ToolRuntime = None
) -> str:
    """
    Complete user registration by updating their profile with full information.
    The user already exists in the system (created on first message), this tool completes their registration.
    
    The user's phone number is automatically retrieved from the agent state - you don't need to provide it.
    
    IMPORTANT: You MUST collect and provide ALL fields:
    - first_name (required)
    - last_name (required)
    - language (required, e.g., 'en', 'es', 'fr', 'he')
    - timezone (required, e.g., 'America/New_York', 'Europe/London', 'Asia/Jerusalem', 'UTC')
    
    Args:
        first_name: User's first name (REQUIRED)
        last_name: User's last name (REQUIRED)
        language: User's preferred language code (REQUIRED)
        timezone: User's timezone (REQUIRED, e.g., 'America/New_York')
    
    Returns:
        Registration status message
    """
    from services.db.users import get_user_by_phone, update_user
    
    # Get phone number from agent state
    phone = runtime.state.get("user_phone")
    if not phone:
        logger.error("user_phone not found in agent state")
        return "Error: Unable to retrieve user phone number from system."
    
    logger.info(f"get_or_create_user called for phone={phone}, first_name={first_name}, last_name={last_name}")
    logger.debug(f"Registration details: language={language}, timezone={timezone}")
    
    try:
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
def send_whatsapp_message(message: str, runtime: ToolRuntime = None) -> str:
    """
    Send a WhatsApp message to a user.
    
    The user's phone number is automatically retrieved from the agent state - you don't need to provide it.
    
    Args:
        message: Message to send
    
    Returns:
        Success or error message
    """
    from services.messages.whatsapp_client import get_whatsapp_client
    
    # Get phone number from agent state
    phone = runtime.state.get("user_phone")
    if not phone:
        logger.error("user_phone not found in agent state")
        return "Error: Unable to retrieve user phone number from system."
    
    logger.info(f"send_whatsapp_message called for phone={phone}")
    logger.debug(f"Message content (first 100 chars): {message[:100]}...")
    
    try:
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
            # Check if already confirmed - treat as success for user experience
            if result.get('already_confirmed'):
                logger.info(f"Event {event_id} was already confirmed - treating as success")
                return f"✓ No worries, this event was already confirmed! 👍"
            
            logger.error(f"Failed to confirm event {event_id}: {result['error']}")
            return f"Error: {result['error']}"
            
    except Exception as e:
        logger.exception(f"Exception in confirm_reminder for event_id {event_id}: {str(e)}")
        return f"Error: {str(e)}"


@tool
def update_reminder(
    event_id: int,
    description: Optional[str] = None,
    event_time: Optional[str] = None,
    recurrence_frequency: Optional[str] = None,
    recurrence_days_of_week: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    Update an existing recurring reminder. This will DELETE all future instances and update the template.
    Use this when the user wants to change the time, description, or recurrence pattern of an existing reminder.
    
    IMPORTANT: This only works for recurring event TEMPLATES (the original event that generates instances).
    To find the template ID, use get_user_reminders to see all reminders and their IDs.
    
    Args:
        event_id: ID of the recurring event template to update
        description: New description (optional - only updates if provided)
        event_time: New time for the reminder (ISO format: YYYY-MM-DD HH:MM:SS, optional)
        recurrence_frequency: New frequency - 'daily', 'weekly', 'monthly', 'yearly' (optional)
        recurrence_days_of_week: New days for weekly recurrence (e.g., "1,3,5", optional)
    
    Returns:
        Success message with details of what was updated, or error message
    """
    from services.db.events import delete_future_instances, update_recurring_event
    from datetime import datetime
    
    logger.info(f"update_reminder called for event_id={event_id}")
    
    try:
        # First, delete all future instances
        logger.debug(f"Deleting future instances for event_id={event_id}")
        delete_result = delete_future_instances(event_id)
        
        if not delete_result['success']:
            logger.error(f"Failed to delete future instances for event_id={event_id}: {delete_result['error']}")
            return f"Error deleting future instances: {delete_result['error']}"
        
        deleted_count = delete_result['deleted_count']
        logger.info(f"Deleted {deleted_count} future instances for event_id={event_id}")
        
        # Parse event_time if provided
        parsed_event_time = None
        if event_time:
            try:
                parsed_event_time = datetime.fromisoformat(event_time)
                logger.debug(f"Parsed event_time: {parsed_event_time}")
            except ValueError as ve:
                logger.error(f"Invalid event_time format: {event_time}")
                return f"Error: Invalid time format. Use YYYY-MM-DD HH:MM:SS"
        
        # Update the recurring event template
        logger.debug(f"Updating recurring event template: event_id={event_id}")
        update_result = update_recurring_event(
            event_id=event_id,
            description=description,
            event_time=parsed_event_time,
            recurrence_frequency=recurrence_frequency,
            recurrence_days_of_week=recurrence_days_of_week
        )
        
        if update_result['success']:
            updated_fields = update_result['updated_fields']
            logger.info(f"Successfully updated event {event_id}: {updated_fields}")
            return f"✓ Reminder updated! Deleted {deleted_count} future instance(s). Updated: {', '.join(updated_fields)}. New instances will be generated with the updated settings."
        else:
            logger.error(f"Failed to update event {event_id}: {update_result['error']}")
            return f"Error updating reminder: {update_result['error']}"
            
    except Exception as e:
        logger.exception(f"Exception in update_reminder for event_id {event_id}: {str(e)}")
        return f"Error: {str(e)}"


@tool
def get_last_messages(n: int = 20, runtime: ToolRuntime = None) -> str:
    """
    Retrieve the last N messages exchanged with a user.
    Use this tool when you need MORE conversation history beyond the automatic 10 messages provided.
    This is helpful for understanding context from earlier in the conversation.
    
    The user's ID is automatically retrieved from the agent state - you don't need to provide it.
    
    Args:
        n: Number of recent messages to retrieve (default: 20, can go higher if needed)
    
    Returns:
        Formatted list of recent messages with timestamps or error
    """
    from services.db.messages import get_last_n_messages
    
    # Get user_id from agent state
    user_id = runtime.state.get("user_id")
    if not user_id:
        logger.error("user_id not found in agent state")
        return "Error: Unable to retrieve user ID from system."
    
    logger.info(f"get_last_messages called for user_id={user_id}, n={n}")
    
    try:
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
def get_pending_reminders(runtime: ToolRuntime = None) -> str:
    """
    Get ONLY pending (unconfirmed) reminders that have been messaged to the user.
    Use this tool when a user responds with confirmation phrases (yes/ok/done/etc.) to help identify
    WHICH specific reminder they are confirming.
    
    The user's ID is automatically retrieved from the agent state - you don't need to provide it.
    
    Returns:
        Formatted list of pending reminders with their descriptions, times, and IDs, or error message
    """
    from services.db.events import Event
    from datetime import datetime, timedelta
    
    # Get user_id from agent state
    user_id = runtime.state.get("user_id")
    if not user_id:
        logger.error("user_id not found in agent state")
        return "Error: Unable to retrieve user ID from system."
    
    logger.info(f"get_pending_reminders called for user_id={user_id}")
    
    try:
        # Get current time - look for events from past 3 hours to current time + 30 minutes
        now = datetime.utcnow()
        three_hours_ago = now - timedelta(hours=3)
        thirty_min_from_now = now + timedelta(minutes=30)
        
        # Query for unconfirmed events that have been messaged
        logger.debug(f"Fetching pending reminders for user_id={user_id}")
        pending_events = Event.query.filter(
            Event.user_id == user_id,
            Event.is_confirmed == False,
            Event.is_message_sent == True,
            Event.parent_event_id != None  # Only instances, not templates
        ).order_by(Event.event_time.asc()).all()
        
        if not pending_events:
            logger.info(f"No pending reminders found for user_id={user_id}")
            return "No pending reminders found."
        
        logger.info(f"Retrieved {len(pending_events)} pending reminder(s) for user_id={user_id}")
        
        # Format events with descriptions and IDs
        formatted = f"⏳ Pending reminders that need confirmation:\n\n"
        for i, event in enumerate(pending_events, 1):
            event_time = datetime.fromisoformat(event.event_time.isoformat()) if hasattr(event.event_time, 'isoformat') else event.event_time
            description = event.description
            event_id = event.id
            
            formatted += f"{i}. Event ID: {event_id}\n"
            formatted += f"   📝 Description: {description}\n"
            formatted += f"   🕐 Time: {event_time.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        logger.debug(f"Formatted {len(pending_events)} pending reminders for user_id={user_id}")
        return formatted
            
    except Exception as e:
        logger.exception(f"Exception in get_pending_reminders for user_id {user_id}: {str(e)}")
        return f"Error: {str(e)}"


@tool
def get_upcoming_reminders(limit: int = 20, runtime: ToolRuntime = None) -> str:
    """
    Get upcoming events/reminders for a user.
    Shows events ordered by time, including confirmation status.
    
    The user's ID is automatically retrieved from the agent state - you don't need to provide it.
    
    Args:
        limit: Maximum number of events to retrieve (default: 20)
    
    Returns:
        Formatted list of upcoming events or error
    """
    from services.db.events import get_upcoming_events
    from datetime import datetime
    
    # Get user_id from agent state
    user_id = runtime.state.get("user_id")
    if not user_id:
        logger.error("user_id not found in agent state")
        return "Error: Unable to retrieve user ID from system."
    
    logger.info(f"get_upcoming_reminders called for user_id={user_id}, limit={limit}")
    
    try:
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
    update_reminder,
    get_last_messages,
    get_pending_reminders,
    get_upcoming_reminders
]
