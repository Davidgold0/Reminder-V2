"""
Background service to generate event instances from recurring templates.
Runs every 30 minutes to ensure we always have instances generated 30 days in advance.

This service is idempotent - it checks for existing instances before creating new ones,
so it's safe to run frequently without creating duplicates.
"""
import os
import sys
from datetime import datetime, timedelta
from flask import has_app_context
from main import create_app, db


def generate_all_instances():
    """
    Generate instances for all recurring event templates.
    Creates instances from today up to 30 days in advance.
    
    Safe to run frequently (every 30 minutes) - only creates instances that don't exist.
    Can be called from within Flask app context or standalone.
    """
    if has_app_context():
        return _generate_all_instances_impl()
    else:
        app = create_app()
        with app.app_context():
            return _generate_all_instances_impl()


def _generate_all_instances_impl():
    """
    Internal implementation of instance generation.
    Assumes we're already in an app context.
    """
    from services.db.events import Event, generate_instances
        
def _generate_all_instances_impl():
    """
    Internal implementation of instance generation.
    Assumes we're already in an app context.
    """
    from services.db.events import Event, generate_instances
    
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=30)
    
    print(f"[{datetime.utcnow()}] Starting instance generation...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Note: Only creating instances that don't already exist\n")
    
    # Get all recurring templates (parent_event_id is None and is_recurring is True)
    recurring_templates = Event.query.filter(
        Event.is_recurring == True,
        Event.parent_event_id == None
    ).all()
    
    print(f"Found {len(recurring_templates)} recurring templates")
    
    total_created = 0
    total_skipped = 0
    
    for template in recurring_templates:
        # Skip if template has ended
        if template.recurrence_end_date and template.recurrence_end_date < start_date:
            print(f"  Skipping template {template.id} - recurrence ended")
            continue
        
        print(f"  Processing template {template.id}: {template.description[:40]}...")
        
        # Count existing instances before generation
        existing_count = Event.query.filter(
            Event.parent_event_id == template.id
        ).count()
        
        result = generate_instances(
            event_id=template.id,
            start_date=start_date,
            end_date=end_date
        )
        
        if result['success']:
            count = result['count']
            total_created += count
            if count > 0:
                print(f"    ✓ Created {count} new instances (had {existing_count} existing)")
            else:
                total_skipped += 1
                print(f"    ↻ All instances already exist ({existing_count} total)")
        else:
            print(f"    ✗ Error: {result['error']}")
    
    print(f"\n[{datetime.utcnow()}] Instance generation complete!")
    print(f"Total NEW instances created: {total_created}")
    print(f"Templates with all instances existing: {total_skipped}")
    print(f"Templates processed: {len(recurring_templates)}")
    
    return {
        'success': True,
        'templates_processed': len(recurring_templates),
        'instances_created': total_created,
        'templates_skipped': total_skipped
    }
if __name__ == '__main__':
    try:
        result = generate_all_instances()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
