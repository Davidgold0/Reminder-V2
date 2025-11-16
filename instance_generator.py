"""
Background service to generate event instances from recurring templates.
Runs daily to ensure we always have instances generated 30 days in advance.

This service should run separately from the main Flask app.
"""
import os
import sys
from datetime import datetime, timedelta
from main import create_app, db


def generate_all_instances():
    """
    Generate instances for all recurring event templates.
    Creates instances from today up to 30 days in advance.
    """
    app = create_app()
    
    with app.app_context():
        from services.db.events import Event, generate_instances
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30)
        
        print(f"[{datetime.utcnow()}] Starting instance generation...")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        
        # Get all recurring templates (parent_event_id is None and is_recurring is True)
        recurring_templates = Event.query.filter(
            Event.is_recurring == True,
            Event.parent_event_id == None
        ).all()
        
        print(f"Found {len(recurring_templates)} recurring templates")
        
        total_created = 0
        for template in recurring_templates:
            # Skip if template has ended
            if template.recurrence_end_date and template.recurrence_end_date < start_date:
                print(f"  Skipping template {template.id} - recurrence ended")
                continue
            
            print(f"  Processing template {template.id}: {template.description[:40]}...")
            
            result = generate_instances(
                event_id=template.id,
                start_date=start_date,
                end_date=end_date
            )
            
            if result['success']:
                count = result['count']
                total_created += count
                print(f"    ✓ Created {count} instances")
            else:
                print(f"    ✗ Error: {result['error']}")
        
        print(f"\n[{datetime.utcnow()}] Instance generation complete!")
        print(f"Total instances created: {total_created}")
        
        return {
            'success': True,
            'templates_processed': len(recurring_templates),
            'instances_created': total_created
        }


if __name__ == '__main__':
    try:
        result = generate_all_instances()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
