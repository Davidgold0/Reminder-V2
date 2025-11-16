"""
Reminder Sender Service - Runs every 30 minutes
Part 1: Sends initial reminders for upcoming unconfirmed events
Part 2: Sends escalating follow-up reminders for events that were already messaged
"""
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app
from services.db.events import Event, mark_message_sent
from services.db.messages import add_message
from services.messages.whatsapp_client import get_whatsapp_client
from services.agent import get_agent
from services.agent_tools import AGENT_TOOLS


def send_initial_reminders():
    """
    Part 1: Send reminders for unconfirmed events happening in the next 30 minutes.
    """
    print(f"\n{'='*60}")
    print(f"Starting initial reminder check at {datetime.utcnow().isoformat()}")
    print(f"{'='*60}\n")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get current time and 30 minutes from now
            now = datetime.utcnow()
            thirty_min_from_now = now + timedelta(minutes=30)
            
            # Query for unconfirmed events in the next 30 minutes that haven't been messaged yet
            upcoming_events = Event.query.filter(
                Event.is_confirmed == False,
                Event.is_message_sent == False,
                Event.event_time >= now,
                Event.event_time <= thirty_min_from_now,
                Event.parent_event_id != None  # Only instances, not templates
            ).all()
            
            print(f"Found {len(upcoming_events)} events needing initial reminders\n")
            
            whatsapp_client = get_whatsapp_client()
            agent = get_agent(tools=AGENT_TOOLS)
            
            for event in upcoming_events:
                try:
                    # Get user info
                    user = event.user
                    user_full_name = f"{user.first_name} {user.last_name}".strip()
                    
                    # Create prompt for agent to generate reminder
                    time_until = event.event_time - now
                    minutes_until = int(time_until.total_seconds() / 60)
                    
                    prompt = f"""Generate a sarcastic, funny, and SHORT reminder message for this event:
Event: {event.description}
Time: {event.event_time.isoformat()} (in {minutes_until} minutes)
User's name: {user_full_name}

This is the FIRST reminder (n=1). Be playful but not too harsh yet.
Keep it under 2 sentences. Make it funny and sarcastic."""
                    
                    # Get AI-generated message
                    reminder_text = agent.process_message(
                        phone=user.phone_number,
                        message=prompt,
                        user_id=user.id,
                        user_full_name=user_full_name,
                        user_language=user.language,
                        user_timezone=user.timezone
                    )
                    
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
    
    app = create_app()
    
    with app.app_context():
        try:
            from services.db.messages import Message
            from sqlalchemy import func
            
            # Get current time and 2 hours ago
            now = datetime.utcnow()
            two_hours_ago = now - timedelta(hours=2)
            
            # Query for unconfirmed events that had messages sent in the last 2 hours
            events_with_messages = Event.query.filter(
                Event.is_confirmed == False,
                Event.is_message_sent == True,
                Event.event_time >= two_hours_ago,
                Event.event_time <= now,
                Event.parent_event_id != None  # Only instances, not templates
            ).all()
            
            print(f"Found {len(events_with_messages)} events with previous messages\n")
            
            whatsapp_client = get_whatsapp_client()
            agent = get_agent(tools=AGENT_TOOLS)
            
            for event in events_with_messages:
                try:
                    # Count how many messages were sent for this event
                    message_count = Message.query.filter(
                        Message.event_id == event.id,
                        Message.sent_by == 'ai'
                    ).count()
                    
                    # Skip if we've already sent 5 messages (n=5 is the max)
                    if message_count >= 5:
                        print(f"⊗ Event {event.id} already has {message_count} messages, skipping")
                        continue
                    
                    # This will be message n (where n starts at 2 since first was already sent)
                    message_number = message_count + 1
                    
                    # Get user info
                    user = event.user
                    user_full_name = f"{user.first_name} {user.last_name}".strip()
                    
                    # Calculate time since event
                    time_since = now - event.event_time
                    minutes_since = int(time_since.total_seconds() / 60)
                    
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

This is reminder #{message_number} (out of 5 max). The user STILL hasn't confirmed!
Tone: {anger_levels.get(message_number, 'annoyed')}
Keep it under 2 sentences. Be {anger_levels.get(message_number, 'annoyed')} but keep it funny and sarcastic."""
                    
                    # Get AI-generated message
                    reminder_text = agent.process_message(
                        phone=user.phone_number,
                        message=prompt,
                        user_id=user.id,
                        user_full_name=user_full_name,
                        user_language=user.language,
                        user_timezone=user.timezone
                    )
                    
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
