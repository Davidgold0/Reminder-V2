from datetime import datetime
from main import db
import logging

# Set up global logger for message database operations
logger = logging.getLogger(__name__)


class Message(db.Model):
    """Message model for storing conversation messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sent_by = db.Column(db.Enum('ai', 'user', name='sender_type'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    required_follow_up = db.Column(db.Boolean, nullable=False, default=False)
    message_text = db.Column(db.Text, nullable=False)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('messages', lazy=True, cascade='all, delete-orphan'))
    event = db.relationship('Event', backref=db.backref('messages', lazy=True))
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sent_by} at {self.timestamp}>'
    
    def to_dict(self):
        """Convert message object to dictionary"""
        return {
            'id': self.id,
            'sent_by': self.sent_by,
            'timestamp': self.timestamp.isoformat(),
            'required_follow_up': self.required_follow_up,
            'message_text': self.message_text,
            'user_id': self.user_id,
            'event_id': self.event_id
        }


# Message Service Functions

def add_message(user_id, sent_by, message_text, required_follow_up=False, event_id=None):
    """
    Add a new message to the database.
    
    Args:
        user_id (int): ID of the user this message belongs to
        sent_by (str): Who sent the message ('ai' or 'user')
        message_text (str): The content of the message
        required_follow_up (bool): Whether this message requires follow-up (default: False)
        event_id (int): Optional ID of the event this message is related to
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - message (dict): Message data if successful
            - error (str): Error message if failed
    """
    logger.info(f"add_message called for user_id={user_id}, sent_by={sent_by}, event_id={event_id}")
    logger.debug(f"Message text (first 100 chars): {message_text[:100]}...")
    logger.debug(f"required_follow_up={required_follow_up}")
    
    try:
        # Validate sent_by value
        if sent_by not in ['ai', 'user']:
            logger.warning(f"Invalid sent_by value: {sent_by}")
            return {
                'success': False,
                'error': "sent_by must be either 'ai' or 'user'"
            }
        
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
        
        # Verify event exists if provided
        if event_id is not None:
            from services.db.events import Event
            logger.debug(f"Verifying event exists: event_id={event_id}")
            event = Event.query.get(event_id)
            if not event:
                logger.error(f"Event with ID {event_id} does not exist")
                return {
                    'success': False,
                    'error': f'Event with ID {event_id} does not exist'
                }
        
        # Create new message
        new_message = Message(
            user_id=user_id,
            sent_by=sent_by,
            message_text=message_text,
            required_follow_up=required_follow_up,
            event_id=event_id
        )
        
        # Add to database
        db.session.add(new_message)
        db.session.commit()
        
        logger.info(f"Successfully created message: id={new_message.id}, user_id={user_id}, "
                   f"sent_by={sent_by}, event_id={event_id}")
        
        return {
            'success': True,
            'message': new_message.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Exception in add_message for user_id {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_last_n_messages(user_id, n=10):
    """
    Get the last n messages for a specific user, ordered by most recent first.
    
    Args:
        user_id (int): ID of the user to get messages for
        n (int): Number of messages to retrieve (default: 10)
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - messages (list): List of message dictionaries if successful
            - count (int): Number of messages returned
            - error (str): Error message if failed
    """
    logger.info(f"get_last_n_messages called for user_id={user_id}, n={n}")
    
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
        
        # Get last n messages ordered by timestamp (most recent first)
        logger.debug(f"Fetching last {n} messages for user_id={user_id}")
        messages = Message.query.filter_by(user_id=user_id)\
            .order_by(Message.timestamp.desc())\
            .limit(n)\
            .all()
        
        logger.info(f"Retrieved {len(messages)} messages for user_id={user_id}")
        
        return {
            'success': True,
            'messages': [msg.to_dict() for msg in messages],
            'count': len(messages)
        }
        
    except Exception as e:
        logger.exception(f"Exception in get_last_n_messages for user_id {user_id}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
