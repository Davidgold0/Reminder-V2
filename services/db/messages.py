from datetime import datetime
from main import db


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
    try:
        # Validate sent_by value
        if sent_by not in ['ai', 'user']:
            return {
                'success': False,
                'error': "sent_by must be either 'ai' or 'user'"
            }
        
        # Verify user exists
        from services.db.users import User
        user = User.query.get(user_id)
        if not user:
            return {
                'success': False,
                'error': f'User with ID {user_id} does not exist'
            }
        
        # Verify event exists if provided
        if event_id is not None:
            from services.db.events import Event
            event = Event.query.get(event_id)
            if not event:
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
        
        return {
            'success': True,
            'message': new_message.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
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
    try:
        # Verify user exists
        from services.db.users import User
        user = User.query.get(user_id)
        if not user:
            return {
                'success': False,
                'error': f'User with ID {user_id} does not exist'
            }
        
        # Get last n messages ordered by timestamp (most recent first)
        messages = Message.query.filter_by(user_id=user_id)\
            .order_by(Message.timestamp.desc())\
            .limit(n)\
            .all()
        
        return {
            'success': True,
            'messages': [msg.to_dict() for msg in messages],
            'count': len(messages)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
