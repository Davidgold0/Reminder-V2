"""
Clean up duplicate event instances - keep only the oldest one for each (parent_event_id, event_time) pair
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app, db
from services.db.events import Event


def clean_duplicates():
    """Remove duplicate event instances, keeping only the first created"""
    print("\n" + "="*80)
    print("CLEANING DUPLICATE EVENT INSTANCES")
    print("="*80 + "\n")
    
    app = create_app()
    with app.app_context():
        # Get all event instances
        instances = Event.query.filter(
            Event.parent_event_id != None
        ).order_by(Event.parent_event_id, Event.event_time, Event.created_at).all()
        
        print(f"Total event instances: {len(instances)}\n")
        
        # Group by (parent_event_id, event_time)
        groups = defaultdict(list)
        for instance in instances:
            key = (instance.parent_event_id, instance.event_time)
            groups[key].append(instance)
        
        # Find duplicates
        duplicates_to_delete = []
        for key, group_instances in groups.items():
            if len(group_instances) > 1:
                # Keep the first one (oldest created_at), delete the rest
                to_keep = group_instances[0]
                to_delete = group_instances[1:]
                duplicates_to_delete.extend(to_delete)
        
        print(f"Found {len(duplicates_to_delete)} duplicate instances to delete\n")
        
        if not duplicates_to_delete:
            print("✅ No duplicates found!")
            return
        
        # Ask for confirmation
        print(f"⚠️  This will DELETE {len(duplicates_to_delete)} duplicate event instances.")
        print("Only the oldest instance for each (parent_event_id, event_time) will be kept.\n")
        
        response = input("Do you want to continue? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\n❌ Operation cancelled.")
            return
        
        # Delete duplicates
        print(f"\n🗑️  Deleting {len(duplicates_to_delete)} duplicates...")
        
        # Get IDs to delete
        ids_to_delete = [inst.id for inst in duplicates_to_delete]
        
        # Bulk delete in batches of 1000
        batch_size = 1000
        total_deleted = 0
        
        for i in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[i:i + batch_size]
            Event.query.filter(Event.id.in_(batch)).delete(synchronize_session=False)
            db.session.commit()
            total_deleted += len(batch)
            print(f"  Deleted {total_deleted}/{len(ids_to_delete)}...")
        
        print(f"\n✅ Successfully deleted {total_deleted} duplicate instances!")
        
        # Show final count
        final_count = Event.query.filter(Event.parent_event_id != None).count()
        print(f"Final event instance count: {final_count}")
        print(f"Removed: {len(instances) - final_count} instances")


if __name__ == "__main__":
    try:
        clean_duplicates()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
