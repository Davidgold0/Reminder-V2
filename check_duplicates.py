"""
Check for duplicate event instances in the database
"""
import os
import sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app
from services.db.events import Event


def check_duplicates():
    """Check for duplicate event instances"""
    print("\n" + "="*80)
    print("DUPLICATE EVENT INSTANCE CHECKER")
    print("="*80 + "\n")
    
    app = create_app()
    with app.app_context():
        # Get all recurring templates
        templates = Event.query.filter(
            Event.is_recurring == True,
            Event.parent_event_id == None
        ).all()
        
        print(f"Found {len(templates)} recurring templates\n")
        
        total_duplicates = 0
        
        for template in templates:
            print(f"\n{'='*80}")
            print(f"Template {template.id}: {template.description}")
            print(f"User: {template.user.first_name} {template.user.last_name}")
            print(f"Frequency: {template.recurrence_frequency}")
            print(f"='*80")
            
            # Get all instances for this template
            instances = Event.query.filter(
                Event.parent_event_id == template.id
            ).order_by(Event.event_time).all()
            
            print(f"Total instances: {len(instances)}")
            
            # Group by event_time to find duplicates
            time_groups = defaultdict(list)
            for instance in instances:
                time_groups[instance.event_time].append(instance)
            
            # Find duplicates
            duplicates = {time: insts for time, insts in time_groups.items() if len(insts) > 1}
            
            if duplicates:
                print(f"⚠️  FOUND {len(duplicates)} DUPLICATE TIME SLOTS with {sum(len(insts) for insts in duplicates.values())} total duplicates")
                total_duplicates += sum(len(insts) - 1 for insts in duplicates.values())
                
                print("\nDuplicate instances:")
                for event_time, duplicate_instances in sorted(duplicates.items()):
                    print(f"\n  Time: {event_time.isoformat()} ({len(duplicate_instances)} instances)")
                    for inst in duplicate_instances:
                        print(f"    - ID: {inst.id}, created: {inst.created_at.isoformat()}, "
                              f"confirmed: {inst.is_confirmed}, msg_sent: {inst.is_message_sent}")
            else:
                print("✅ No duplicates found")
            
            # Show instance distribution
            print(f"\nInstance timeline:")
            unique_times = sorted(time_groups.keys())
            if len(unique_times) > 10:
                print(f"  First 5 instances:")
                for t in unique_times[:5]:
                    count = len(time_groups[t])
                    marker = "⚠️ " if count > 1 else "  "
                    print(f"  {marker}{t.isoformat()} ({count} instance{'s' if count > 1 else ''})")
                print(f"  ... ({len(unique_times) - 10} more) ...")
                print(f"  Last 5 instances:")
                for t in unique_times[-5:]:
                    count = len(time_groups[t])
                    marker = "⚠️ " if count > 1 else "  "
                    print(f"  {marker}{t.isoformat()} ({count} instance{'s' if count > 1 else ''})")
            else:
                for t in unique_times:
                    count = len(time_groups[t])
                    marker = "⚠️ " if count > 1 else "  "
                    print(f"  {marker}{t.isoformat()} ({count} instance{'s' if count > 1 else ''})")
        
        print(f"\n\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total templates: {len(templates)}")
        print(f"Total duplicate instances: {total_duplicates}")
        
        if total_duplicates > 0:
            print(f"\n⚠️  WARNING: Found {total_duplicates} duplicate instances!")
            print("This means the instance generator is creating duplicates instead of checking for existing ones.")
        else:
            print("\n✅ No duplicates found - instance generator is working correctly")


if __name__ == "__main__":
    check_duplicates()
