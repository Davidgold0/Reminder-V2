"""
Reminder Sender Service - Runs every 30 minutes
Part 1: Sends initial reminders for upcoming unconfirmed events
Part 2: Sends escalating follow-up reminders for events that were already messaged
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import has_app_context

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app
from services.db.events import Event, mark_message_sent
from services.db.messages import add_message
from services.messages.whatsapp_client import get_whatsapp_client
from langchain_openai import ChatOpenAI
from config import Config


def send_initial_reminders():
    """
    Part 1: Send reminders for unconfirmed events happening in the next 30 minutes.
    """
    print(f"\n{'='*60}")
    print(f"Starting initial reminder check at {datetime.utcnow().isoformat()}")
    print(f"{'='*60}\n")
    
    # Only create app context if not already in one (e.g., when called from Flask endpoint)
    if has_app_context():
        _send_initial_reminders_impl()
    else:
        app = create_app()
        with app.app_context():
            _send_initial_reminders_impl()


def _send_initial_reminders_impl():
    """Implementation of initial reminder sending (assumes app context exists)"""
    try:
        # Get current time (UTC)
        now = datetime.utcnow()
        thirty_min_from_now = now + timedelta(minutes=30)
        
        # Query for unconfirmed events that haven't been messaged yet
        # We'll filter by time in Python since events are stored in user's local timezone
        candidate_events = Event.query.filter(
            Event.is_confirmed == False,
            Event.is_message_sent == False,
            Event.parent_event_id != None  # Only instances, not templates
        ).all()
        
        # Filter events that are 30 minutes away (in their user's timezone converted to UTC)
        # Using < instead of <= to avoid sending at the exact event time
        upcoming_events = []
        for event in candidate_events:
            user_tz = ZoneInfo(event.user.timezone or 'UTC')
            # Event time is stored as naive datetime in user's timezone
            event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
            event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
            
            # Check if event is in the next 30 minutes (but hasn't started yet)
            if now < event_time_utc <= thirty_min_from_now:
                upcoming_events.append(event)
        
        print(f"Found {len(upcoming_events)} events needing initial reminders (out of {len(candidate_events)} candidates)\n")
        
        whatsapp_client = get_whatsapp_client()
        
        # Initialize simple ChatOpenAI model (no tools, no system prompt)
        model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=Config.OPENAI_API_KEY
        )
        
        for event in upcoming_events:
            try:
                # Get user info
                user = event.user
                user_full_name = f"{user.first_name} {user.last_name}".strip()
                
                # Convert event time from user's timezone to UTC for comparison
                user_tz = ZoneInfo(user.timezone or 'UTC')
                # Event time is stored as naive datetime in user's timezone
                event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
                event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC'))
                
                # Create prompt for model to generate reminder
                time_until = event_time_utc.replace(tzinfo=None) - now
                minutes_until = int(time_until.total_seconds() / 60)
                user_language = user.language or 'en'
                
                prompt = f"""Generate a sarcastic, funny, and SHORT reminder message for this event:
Event: {event.description}
Time: {event.event_time.isoformat()} (in {minutes_until} minutes)
User's name: {user_full_name}
Language: {user_language}

IMPORTANT: Write the ENTIRE message in {user_language} language!
This is the FIRST reminder (n=1). Be playful but not too harsh yet.
Keep it under 2 sentences. Make it funny and sarcastic."""
                
                # Get AI-generated message using simple model invocation
                response = model.invoke(prompt)
                reminder_text = response.content
                
                # Send via WhatsApp
                result = whatsapp_client.send_message(
                    phone=user.phone_number,
                    message=reminder_text
                )
                
                if result['success']:
                    # Save message to database
                    msg_result = add_message(
                        user_id=user.id,
                        sent_by='ai',
                        message_text=reminder_text,
                        required_follow_up=True,
                        event_id=event.id
                    )
                    
                    # Mark event as message sent
                    mark_message_sent(event.id)
                    
                    print(f"✓ Sent initial reminder for event {event.id} to {user.phone_number}")
                    print(f"  Message: {reminder_text[:100]}...")
                else:
                    print(f"✗ Failed to send reminder for event {event.id}: {result.get('error')}")
                    
            except Exception as e:
                print(f"✗ Error processing event {event.id}: {e}")
                continue
        
        print(f"\nInitial reminders completed: {len(upcoming_events)} processed")
        
    except Exception as e:
        print(f"Error in initial reminder process: {e}")
        import traceback
        traceback.print_exc()


def send_escalating_reminders():
    """
    Part 2: Send escalating reminders for events that were messaged in the last 2 hours
    but still haven't been confirmed. Messages get progressively angrier (n=2 to n=5).
    """
    print(f"\n{'='*60}")
    print(f"Starting escalating reminder check at {datetime.utcnow().isoformat()}")
    print(f"{'='*60}\n")
    
    # Only create app context if not already in one (e.g., when called from Flask endpoint)
    if has_app_context():
        _send_escalating_reminders_impl()
    else:
        app = create_app()
        with app.app_context():
            _send_escalating_reminders_impl()


def _send_escalating_reminders_impl():
    """Implementation of escalating reminder sending (assumes app context exists)"""
    try:
        from services.db.messages import Message
        from sqlalchemy import func
        
        # Get current time (UTC) and 3 hours ago
        now = datetime.utcnow()
        three_hours_ago = now - timedelta(hours=3)
        
        # Query for unconfirmed events that had messages sent
        # We'll filter by time in Python since events are stored in user's local timezone
        candidate_events = Event.query.filter(
            Event.is_confirmed == False,
            Event.is_message_sent == True,
            Event.parent_event_id != None  # Only instances, not templates
        ).all()
        
        # Filter events where event time was in the last 3 hours (in UTC)
        # Extended to 3 hours to ensure we catch events that need follow-ups
        events_with_messages = []
        for event in candidate_events:
            user_tz = ZoneInfo(event.user.timezone or 'UTC')
            # Event time is stored as naive datetime in user's timezone
            event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
            event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
            
            # Check if event time was in the last 3 hours
            if three_hours_ago <= event_time_utc <= now:
                events_with_messages.append(event)
        
        print(f"Found {len(events_with_messages)} events with previous messages (out of {len(candidate_events)} candidates)\n")
        
        whatsapp_client = get_whatsapp_client()
        
        # Initialize simple ChatOpenAI model (no tools, no system prompt)
        model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=Config.OPENAI_API_KEY
        )
        
        for event in events_with_messages:
            try:
                # Get all messages for this event to check count and timing
                event_messages = Message.query.filter(
                    Message.event_id == event.id,
                    Message.sent_by == 'ai'
                ).order_by(Message.timestamp.desc()).all()
                
                message_count = len(event_messages)
                
                # Skip if we've already sent 5 messages (n=5 is the max)
                if message_count >= 5:
                    print(f"⊗ Event {event.id} already has {message_count} messages, skipping")
                    continue
                
                # Check if enough time has passed since the last message (at least 30 minutes)
                if event_messages:
                    last_message = event_messages[0]  # Most recent
                    time_since_last_message = now - last_message.timestamp
                    minutes_since_last = int(time_since_last_message.total_seconds() / 60)
                    
                    if minutes_since_last < 30:
                        print(f"⊗ Event {event.id}: Only {minutes_since_last} minutes since last message, skipping")
                        continue
                
                # This will be message n (where n starts at 2 since first was already sent)
                message_number = message_count + 1
                
                # Get user info
                user = event.user
                user_full_name = f"{user.first_name} {user.last_name}".strip()
                
                # Convert event time from user's timezone to UTC for comparison
                user_tz = ZoneInfo(user.timezone or 'UTC')
                # Event time is stored as naive datetime in user's timezone
                event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
                event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC'))
                
                # Calculate time since event
                time_since = now - event_time_utc.replace(tzinfo=None)
                minutes_since = int(time_since.total_seconds() / 60)
                user_language = user.language or 'en'
                
                # Create escalating prompt based on message number
                anger_levels = {
                    2: "slightly annoyed",
                    3: "getting frustrated",
                    4: "pretty angry now",
                    5: "absolutely livid (but still funny)"
                }
                
                prompt = f"""Generate a sarcastic, funny, and SHORT follow-up reminder for this event:
Event: {event.description}
Time: {event.event_time.isoformat()} (was {minutes_since} minutes ago)
User's name: {user_full_name}
Language: {user_language}

IMPORTANT: Write the ENTIRE message in {user_language} language!
This is reminder #{message_number} (out of 5 max). The user STILL hasn't confirmed!
Tone: {anger_levels.get(message_number, 'annoyed')}
Keep it under 2 sentences. Be {anger_levels.get(message_number, 'annoyed')} but keep it funny and sarcastic."""
                
                # Get AI-generated message using simple model invocation
                response = model.invoke(prompt)
                reminder_text = response.content
                
                # Send via WhatsApp
                result = whatsapp_client.send_message(
                    phone=user.phone_number,
                    message=reminder_text
                )
                
                if result['success']:
                    # Save message to database
                    add_message(
                        user_id=user.id,
                        sent_by='ai',
                        message_text=reminder_text,
                        required_follow_up=True,
                        event_id=event.id
                    )
                    
                    print(f"✓ Sent escalating reminder #{message_number} for event {event.id} to {user.phone_number}")
                    print(f"  Message: {reminder_text[:100]}...")
                else:
                    print(f"✗ Failed to send escalating reminder for event {event.id}: {result.get('error')}")
                    
            except Exception as e:
                print(f"✗ Error processing event {event.id}: {e}")
                continue
        
        print(f"\nEscalating reminders completed: {len(events_with_messages)} processed")
        
    except Exception as e:
        print(f"Error in escalating reminder process: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run both reminder processes"""
    print("\n" + "="*60)
    print("REMINDER SENDER SERVICE STARTED")
    print("="*60)
    
    # Part 1: Send initial reminders for upcoming events
    send_initial_reminders()
    
    # Part 2: Send escalating reminders for past events
    send_escalating_reminders()
    
    print("\n" + "="*60)
    print("REMINDER SENDER SERVICE COMPLETED")
    print("="*60 + "\n")
    
    return {
        'success': True,
        'message': 'Reminder processes completed'
    }


if __name__ == "__main__":
    main()
