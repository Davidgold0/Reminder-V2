"""
Test script to simulate reminder logic and debug why you're getting duplicate messages
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app
from services.db.events import Event
from services.db.messages import Message


def test_initial_reminders():
    """Test Part 1: Initial reminder logic"""
    print("\n" + "="*80)
    print("TESTING INITIAL REMINDERS LOGIC")
    print("="*80 + "\n")
    
    app = create_app()
    with app.app_context():
        now = datetime.utcnow()
        thirty_min_from_now = now + timedelta(minutes=30)
        
        print(f"Current time (UTC): {now.isoformat()}")
        print(f"Looking for events between: {now.isoformat()} and {thirty_min_from_now.isoformat()}\n")
        
        # Step 1: Query candidates
        candidate_events = Event.query.filter(
            Event.is_confirmed == False,
            Event.is_message_sent == False,
            Event.parent_event_id != None
        ).all()
        
        print(f"📊 STEP 1: Database query results")
        print(f"   Found {len(candidate_events)} candidate events (unconfirmed, no message sent, is instance)\n")
        
        if candidate_events:
            print("   Candidate events:")
            for event in candidate_events:
                print(f"   - Event {event.id}: {event.description}")
                print(f"     User: {event.user.first_name} {event.user.last_name} (timezone: {event.user.timezone})")
                print(f"     Event time (stored): {event.event_time.isoformat()}")
                print(f"     is_confirmed: {event.is_confirmed}")
                print(f"     is_message_sent: {event.is_message_sent}")
                print(f"     parent_event_id: {event.parent_event_id}")
                print()
        
        # Step 2: Filter by time
        upcoming_events = []
        print(f"📊 STEP 2: Time filtering")
        for event in candidate_events:
            user_tz = ZoneInfo(event.user.timezone or 'UTC')
            event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
            event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
            
            time_diff = (event_time_utc - now).total_seconds() / 60
            passes_filter = now < event_time_utc <= thirty_min_from_now
            
            print(f"   Event {event.id}:")
            print(f"     Event time in UTC: {event_time_utc.isoformat()}")
            print(f"     Time until event: {time_diff:.1f} minutes")
            print(f"     Passes filter (now < event <= 30min): {passes_filter}")
            
            if passes_filter:
                upcoming_events.append(event)
                print(f"     ✅ WILL SEND INITIAL REMINDER")
            else:
                print(f"     ❌ Will NOT send (outside time window)")
            print()
        
        print(f"📊 RESULT: {len(upcoming_events)} events will get INITIAL reminders\n")


def test_escalating_reminders():
    """Test Part 2: Escalating reminder logic"""
    print("\n" + "="*80)
    print("TESTING ESCALATING REMINDERS LOGIC")
    print("="*80 + "\n")
    
    app = create_app()
    with app.app_context():
        now = datetime.utcnow()
        three_hours_ago = now - timedelta(hours=3)
        
        print(f"Current time (UTC): {now.isoformat()}")
        print(f"Looking for events between: {three_hours_ago.isoformat()} and {now.isoformat()}\n")
        
        # Step 1: Query candidates
        candidate_events = Event.query.filter(
            Event.is_confirmed == False,
            Event.is_message_sent == True,  # Already has message
            Event.parent_event_id != None
        ).all()
        
        print(f"📊 STEP 1: Database query results")
        print(f"   Found {len(candidate_events)} candidate events (unconfirmed, message sent, is instance)\n")
        
        if candidate_events:
            print("   Candidate events:")
            for event in candidate_events:
                print(f"   - Event {event.id}: {event.description}")
                print(f"     User: {event.user.first_name} {event.user.last_name} (timezone: {event.user.timezone})")
                print(f"     Event time (stored): {event.event_time.isoformat()}")
                print(f"     is_confirmed: {event.is_confirmed}")
                print(f"     is_message_sent: {event.is_message_sent}")
                print()
        
        # Step 2: Filter by time
        events_with_messages = []
        print(f"📊 STEP 2: Time filtering")
        for event in candidate_events:
            user_tz = ZoneInfo(event.user.timezone or 'UTC')
            event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
            event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
            
            time_diff = (now - event_time_utc).total_seconds() / 60
            passes_filter = three_hours_ago <= event_time_utc <= now
            
            print(f"   Event {event.id}:")
            print(f"     Event time in UTC: {event_time_utc.isoformat()}")
            print(f"     Time since event: {time_diff:.1f} minutes ago")
            print(f"     Passes filter (3h ago <= event <= now): {passes_filter}")
            
            if passes_filter:
                events_with_messages.append(event)
            print()
        
        print(f"📊 STEP 3: Message count and timing checks")
        final_events = []
        for event in events_with_messages:
            # Get message history
            event_messages = Message.query.filter(
                Message.event_id == event.id,
                Message.sent_by == 'ai'
            ).order_by(Message.timestamp.desc()).all()
            
            message_count = len(event_messages)
            
            print(f"   Event {event.id}:")
            print(f"     Total AI messages sent: {message_count}")
            
            if message_count >= 5:
                print(f"     ❌ Already sent max (5) messages, SKIP")
                continue
            
            if event_messages:
                last_message = event_messages[0]
                time_since_last = (now - last_message.timestamp).total_seconds() / 60
                print(f"     Last message sent: {last_message.timestamp.isoformat()}")
                print(f"     Time since last message: {time_since_last:.1f} minutes")
                
                if time_since_last < 30:
                    print(f"     ❌ Too soon (need 30 min), SKIP")
                    continue
                else:
                    print(f"     ✅ Enough time passed")
            
            next_message_num = message_count + 1
            print(f"     ✅ WILL SEND ESCALATING REMINDER #{next_message_num}")
            final_events.append(event)
            print()
        
        print(f"📊 RESULT: {len(final_events)} events will get ESCALATING reminders\n")


def show_all_events_summary():
    """Show a summary of all events in the database"""
    print("\n" + "="*80)
    print("RELEVANT EVENTS IN DATABASE (upcoming + recent only)")
    print("="*80 + "\n")
    
    app = create_app()
    with app.app_context():
        now = datetime.utcnow()
        three_hours_ago = now - timedelta(hours=3)
        thirty_min_from_now = now + timedelta(minutes=30)
        
        # Get only event instances (not templates)
        all_events = Event.query.filter(Event.parent_event_id != None).all()
        
        # Filter to only events in time window (converted to UTC)
        relevant_events = []
        for event in all_events:
            user_tz = ZoneInfo(event.user.timezone or 'UTC')
            event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
            event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
            
            # Keep if event is within 3 hours ago to 30 min from now
            if three_hours_ago <= event_time_utc <= thirty_min_from_now:
                relevant_events.append(event)
        
        print(f"Total event instances: {len(all_events)}")
        print(f"Relevant events (past 3h to next 30min): {len(relevant_events)}\n")
        
        if not relevant_events:
            print("⚠️  No relevant events found in the time window")
            print(f"   Looking for events between:")
            print(f"   {three_hours_ago.isoformat()} (3h ago)")
            print(f"   and {thirty_min_from_now.isoformat()} (30min from now)")
            return
        
        for event in relevant_events:
            user_tz = ZoneInfo(event.user.timezone or 'UTC')
            event_time_user_tz = event.event_time.replace(tzinfo=user_tz)
            event_time_utc = event_time_user_tz.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
            time_diff = (event_time_utc - now).total_seconds() / 60
            
            print(f"Event {event.id}: {event.description}")
            print(f"  User: {event.user.first_name} {event.user.last_name} (timezone: {event.user.timezone})")
            print(f"  Event time (local): {event.event_time.isoformat()}")
            print(f"  Event time (UTC): {event_time_utc.isoformat()}")
            print(f"  Time diff: {time_diff:.1f} minutes {'from now' if time_diff > 0 else 'ago'}")
            print(f"  is_confirmed: {event.is_confirmed}")
            print(f"  is_message_sent: {event.is_message_sent}")
            print(f"  parent_event_id: {event.parent_event_id}")
            
            # Get message count
            messages = Message.query.filter(
                Message.event_id == event.id,
                Message.sent_by == 'ai'
            ).all()
            print(f"  AI messages sent: {len(messages)}")
            if messages:
                for i, msg in enumerate(messages, 1):
                    print(f"    #{i}: {msg.timestamp.isoformat()} - {msg.message_text[:60]}...")
            print()


def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("REMINDER LOGIC DEBUGGER - Finding why you get duplicate messages")
    print("#"*80)
    
    # Show all events first
    show_all_events_summary()
    
    # Test initial reminder logic
    test_initial_reminders()
    
    # Test escalating reminder logic
    test_escalating_reminders()
    
    print("\n" + "#"*80)
    print("ANALYSIS COMPLETE")
    print("#"*80)
    print("\n💡 KEY POINTS:")
    print("   - Initial reminders: is_message_sent = False AND event in next 30 min")
    print("   - Escalating reminders: is_message_sent = True AND event was 0-3 hours ago")
    print("   - If BOTH conditions match, you'll get 2 messages!")
    print("\n🔍 Look above to see which events pass which filters.\n")


if __name__ == "__main__":
    main()
