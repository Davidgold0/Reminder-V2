from datetime import datetime
from main import db
import logging

# Set up global logger for event database operations
logger = logging.getLogger(__name__)


class Event(db.Model):
    """Event model for storing user events and reminders"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Basic event fields
    description = db.Column(db.String(500), nullable=False)
    event_time = db.Column(db.DateTime, nullable=False, index=True)
    is_message_sent = db.Column(db.Boolean, nullable=False, default=False)
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Recurrence fields
    is_recurring = db.Column(db.Boolean, nullable=False, default=False)
    recurrence_frequency = db.Column(
        db.Enum('daily', 'weekly', 'monthly', 'yearly', name='frequency_type'), 
        nullable=True
    )
    recurrence_interval = db.Column(db.Integer, nullable=True, default=1)  # e.g., every 2 days
    recurrence_end_date = db.Column(db.DateTime, nullable=True)
    recurrence_days_of_week = db.Column(db.String(20), nullable=True)  # e.g., "1,3,5" for Mon,Wed,Fri
    
    # Self-referencing for generated instances
    parent_event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('events', lazy=True))
    parent_event = db.relationship('Event', remote_side=[id], backref='instances')
    
    def __repr__(self):
        return f'<Event {self.id}: {self.description[:30]}... at {self.event_time}>'
    
    def to_dict(self):
        """Convert event object to dictionary"""
        return {
            'id': self.id,
            'description': self.description,
            'event_time': self.event_time.isoformat(),
            'is_message_sent': self.is_message_sent,
            'is_confirmed': self.is_confirmed,
            'user_id': self.user_id,
            'is_recurring': self.is_recurring,
            'recurrence_frequency': self.recurrence_frequency,
            'recurrence_interval': self.recurrence_interval,
            'recurrence_end_date': self.recurrence_end_date.isoformat() if self.recurrence_end_date else None,
            'recurrence_days_of_week': self.recurrence_days_of_week,
            'parent_event_id': self.parent_event_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# Event Service Functions

def add_event(user_id, description, event_time, is_recurring=False, 
              recurrence_frequency=None, recurrence_interval=1, 
              recurrence_end_date=None, recurrence_days_of_week=None):
    """
    Add a new event (one-time or recurring template) to the database.
    
    Args:
        user_id (int): ID of the user this event belongs to
        description (str): Description of the event
        event_time (datetime): Time of the event
        is_recurring (bool): Whether this is a recurring event (default: False)
        recurrence_frequency (str): Frequency ('daily', 'weekly', 'monthly', 'yearly')
        recurrence_interval (int): Interval for recurrence (e.g., every 2 days)
        recurrence_end_date (datetime): When to stop recurring (optional)
        recurrence_days_of_week (str): Days of week for weekly recurrence (e.g., "1,3,5")
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - event (dict): Event data if successful
            - error (str): Error message if failed
    """
    logger.info(f"add_event called for user_id={user_id}, is_recurring={is_recurring}")
    logger.debug(f"Event details: description='{description}', event_time={event_time}, "
                 f"recurrence_frequency={recurrence_frequency}, recurrence_interval={recurrence_interval}, "
                 f"recurrence_days_of_week={recurrence_days_of_week}")
    
    try:
        # Verify user exists
        from services.db.users import User
        logger.debug(f"Verifying user exists: user_id={user_id}")
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} does not exist")
            return {
                'success': False,
                'error': f'User with ID {user_id} does not exist'
            }
        
        # Validate recurring fields
        if is_recurring:
            logger.debug("Validating recurring event fields")
            if not recurrence_frequency:
                logger.warning(f"Recurring event missing recurrence_frequency for user_id={user_id}")
                return {
                    'success': False,
                    'error': 'recurrence_frequency is required for recurring events'
                }
            if recurrence_frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
                logger.warning(f"Invalid recurrence_frequency '{recurrence_frequency}' for user_id={user_id}")
                return {
                    'success': False,
                    'error': 'recurrence_frequency must be daily, weekly, monthly, or yearly'
                }
        
        # Create new event
        new_event = Event(
            user_id=user_id,
            description=description,
            event_time=event_time,
            is_recurring=is_recurring,
            recurrence_frequency=recurrence_frequency if is_recurring else None,
            recurrence_interval=recurrence_interval if is_recurring else None,
            recurrence_end_date=recurrence_end_date,
            recurrence_days_of_week=recurrence_days_of_week
        )
        
        # Add to database
        db.session.add(new_event)
        db.session.commit()
        
        logger.info(f"Successfully created {'recurring' if is_recurring else 'one-time'} event: "
                   f"id={new_event.id}, user_id={user_id}, description='{description}'")
        
        return {
            'success': True,
            'event': new_event.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Exception in add_event for user_id {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def generate_instances(event_id, start_date, end_date):
    """
    Generate event instances from a recurring template for a specific date range.
    
    Args:
        event_id (int): ID of the recurring event template
        start_date (datetime): Start of the date range
        end_date (datetime): End of the date range
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - instances (list): List of created instance dictionaries
            - count (int): Number of instances created
            - error (str): Error message if failed
    """
    from datetime import timedelta
    
    logger.info(f"generate_instances called for event_id={event_id}, "
               f"start_date={start_date}, end_date={end_date}")
    
    try:
        # Get the template event
        logger.debug(f"Fetching template event: event_id={event_id}")
        template = Event.query.get(event_id)
        if not template:
            logger.error(f"Event with ID {event_id} does not exist")
            return {
                'success': False,
                'error': f'Event with ID {event_id} does not exist'
            }
        
        if not template.is_recurring:
            logger.warning(f"Event {event_id} is not a recurring template")
            return {
                'success': False,
                'error': 'Event is not a recurring template'
            }
        
        if template.parent_event_id is not None:
            logger.warning(f"Event {event_id} is an instance, not a template")
            return {
                'success': False,
                'error': 'Cannot generate instances from an instance. Use the parent event.'
            }
        
        instances = []
        current_date = start_date
        
        # Check if we should stop at recurrence_end_date
        effective_end_date = end_date
        if template.recurrence_end_date and template.recurrence_end_date < end_date:
            effective_end_date = template.recurrence_end_date
        
        while current_date <= effective_end_date:
            should_create = False
            
            if template.recurrence_frequency == 'daily':
                should_create = True
            
            elif template.recurrence_frequency == 'weekly':
                # Check if current day of week matches
                if template.recurrence_days_of_week:
                    days = [int(d) for d in template.recurrence_days_of_week.split(',')]
                    # 0 = Monday, 6 = Sunday in Python
                    if current_date.weekday() in days:
                        should_create = True
                else:
                    # No specific days, use the same day of week as template
                    if current_date.weekday() == template.event_time.weekday():
                        should_create = True
            
            elif template.recurrence_frequency == 'monthly':
                # Same day of month as template
                if current_date.day == template.event_time.day:
                    should_create = True
            
            elif template.recurrence_frequency == 'yearly':
                # Same month and day as template
                if current_date.month == template.event_time.month and current_date.day == template.event_time.day:
                    should_create = True
            
            if should_create:
                # Check if instance already exists for this date
                instance_time = current_date.replace(
                    hour=template.event_time.hour,
                    minute=template.event_time.minute,
                    second=template.event_time.second
                )
                
                existing = Event.query.filter_by(
                    parent_event_id=event_id,
                    event_time=instance_time
                ).first()
                
                if not existing:
                    # Create new instance
                    instance = Event(
                        user_id=template.user_id,
                        description=template.description,
                        event_time=instance_time,
                        is_recurring=False,
                        parent_event_id=event_id
                    )
                    db.session.add(instance)
                    instances.append(instance)
            
            # Move to next interval
            if template.recurrence_frequency == 'daily':
                current_date += timedelta(days=template.recurrence_interval)
            elif template.recurrence_frequency == 'weekly':
                current_date += timedelta(days=1)
            elif template.recurrence_frequency == 'monthly':
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            elif template.recurrence_frequency == 'yearly':
                current_date = current_date.replace(year=current_date.year + 1)
        
        db.session.commit()
        
        logger.info(f"Successfully generated {len(instances)} instances for event_id={event_id}")
        
        return {
            'success': True,
            'instances': [inst.to_dict() for inst in instances],
            'count': len(instances)
        }
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Exception in generate_instances for event_id {event_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_upcoming_events(user_id, start_time=None, end_time=None, limit=50):
    """
    Get upcoming events for a user (includes one-time events and generated instances).
    
    Args:
        user_id (int): ID of the user
        start_time (datetime): Start time filter (default: now)
        end_time (datetime): End time filter (optional)
        limit (int): Maximum number of events to return (default: 50)
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - events (list): List of event dictionaries ordered by time
            - count (int): Number of events returned
            - error (str): Error message if failed
    """
    logger.info(f"get_upcoming_events called for user_id={user_id}, limit={limit}")
    logger.debug(f"Time filters: start_time={start_time}, end_time={end_time}")
    
    try:
        from services.db.users import User
        
        # Verify user exists
        logger.debug(f"Verifying user exists: user_id={user_id}")
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} does not exist")
            return {
                'success': False,
                'error': f'User with ID {user_id} does not exist'
            }
        
        # Default start time is one day before now
        if start_time is None:
            from datetime import timedelta
            start_time = datetime.utcnow() - timedelta(days=1)
            logger.debug(f"Using default start_time: {start_time}")
        
        # Build query - exclude recurring templates (parent_event_id is None and is_recurring is True)
        query = Event.query.filter(
            Event.user_id == user_id,
            Event.event_time >= start_time,
            db.or_(
                Event.is_recurring == False,  # One-time events
                Event.parent_event_id != None  # Generated instances
            )
        )
        
        if end_time:
            query = query.filter(Event.event_time <= end_time)
        
        events = query.order_by(Event.event_time.asc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(events)} upcoming events for user_id={user_id}")
        
        return {
            'success': True,
            'events': [event.to_dict() for event in events],
            'count': len(events)
        }
        
    except Exception as e:
        logger.exception(f"Exception in get_upcoming_events for user_id {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_events_needing_message(start_time=None, end_time=None):
    """
    Get all events that need a message sent (is_message_sent = False).
    Useful for a background job to process pending reminders.
    
    Args:
        start_time (datetime): Start time filter (default: now)
        end_time (datetime): End time filter (optional)
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - events (list): List of event dictionaries that need messages
            - count (int): Number of events returned
            - error (str): Error message if failed
    """
    logger.info(f"get_events_needing_message called")
    logger.debug(f"Time filters: start_time={start_time}, end_time={end_time}")
    
    try:
        # Default start time is now
        if start_time is None:
            start_time = datetime.utcnow()
            logger.debug(f"Using default start_time: {start_time}")
        
        # Build query - only events that haven't been sent yet
        query = Event.query.filter(
            Event.is_message_sent == False,
            Event.event_time >= start_time,
            db.or_(
                Event.is_recurring == False,  # One-time events
                Event.parent_event_id != None  # Generated instances
            )
        )
        
        if end_time:
            query = query.filter(Event.event_time <= end_time)
        
        events = query.order_by(Event.event_time.asc()).all()
        
        logger.info(f"Retrieved {len(events)} events needing messages")
        
        return {
            'success': True,
            'events': [event.to_dict() for event in events],
            'count': len(events)
        }
        
    except Exception as e:
        logger.exception(f"Exception in get_events_needing_message: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def mark_message_sent(event_id):
    """
    Mark an event as having its message sent.
    
    Args:
        event_id (int): ID of the event
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - event (dict): Updated event data if successful
            - error (str): Error message if failed
    """
    logger.info(f"mark_message_sent called for event_id={event_id}")
    
    try:
        logger.debug(f"Fetching event: event_id={event_id}")
        event = Event.query.get(event_id)
        if not event:
            logger.error(f"Event with ID {event_id} does not exist")
            return {
                'success': False,
                'error': f'Event with ID {event_id} does not exist'
            }
        
        # Update the event
        event.is_message_sent = True
        event.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Successfully marked message as sent for event_id={event_id}")
        
        return {
            'success': True,
            'event': event.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Exception in mark_message_sent for event_id {event_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def confirm_event(event_id: int) -> dict:
    """
    Mark an event as confirmed.
    
    Args:
        event_id: ID of the event to confirm
        
    Returns:
        dict: Result with success status and event details or error message
    """
    logger.info(f"confirm_event called for event_id={event_id}")
    
    try:
        # Get the event
        logger.debug(f"Fetching event: event_id={event_id}")
        event = Event.query.get(event_id)
        
        if not event:
            logger.error(f"Event with ID {event_id} does not exist")
            return {
                'success': False,
                'error': f'Event with ID {event_id} does not exist'
            }
        
        # Update the event
        event.is_confirmed = True
        event.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Successfully confirmed event: event_id={event_id}, description='{event.description}'")
        
        return {
            'success': True,
            'event': event.to_dict(),
            'message': f'Event "{event.description}" has been confirmed'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Exception in confirm_event for event_id {event_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
