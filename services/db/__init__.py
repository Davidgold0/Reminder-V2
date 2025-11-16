"""
Database models package.
Contains all database models and their service functions.
"""
from services.db.users import User, add_user, get_user_by_phone
from services.db.messages import Message, add_message, get_last_n_messages
from services.db.events import (
    Event, 
    add_event, 
    generate_instances, 
    get_upcoming_events, 
    get_events_needing_message,
    mark_message_sent,
    confirm_event
)

__all__ = [
    'User', 'add_user', 'get_user_by_phone',
    'Message', 'add_message', 'get_last_n_messages',
    'Event', 'add_event', 'generate_instances', 'get_upcoming_events', 
    'get_events_needing_message', 'mark_message_sent', 'confirm_event'
]
