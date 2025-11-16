from datetime import datetime
from main import db


class User(db.Model):
    """User model for storing user information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    timezone = db.Column(db.String(50), nullable=False, default='UTC')
    language = db.Column(db.String(10), nullable=False, default='en')
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.first_name} {self.last_name} ({self.phone_number})>'
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'timezone': self.timezone,
            'language': self.language,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# User Service Functions

def add_user(first_name, last_name, phone_number, timezone='UTC', language='en'):
    """
    Add a new user to the database.
    
    Args:
        first_name (str): User's first name
        last_name (str): User's last name
        phone_number (str): User's phone number (must be unique)
        timezone (str): User's timezone (default: 'UTC')
        language (str): User's preferred language (default: 'en')
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - user (dict): User data if successful
            - error (str): Error message if failed
    
    Raises:
        None: All exceptions are caught and returned in the response
    """
    try:
        # Check if user with this phone number already exists
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            return {
                'success': False,
                'error': f'User with phone number {phone_number} already exists'
            }
        
        # Create new user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            timezone=timezone,
            language=language
        )
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        return {
            'success': True,
            'user': new_user.to_dict()
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


def get_user_by_phone(phone_number):
    """
    Search for a user by phone number.
    
    Args:
        phone_number (str): The phone number to search for
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - user (dict): User data if found
            - error (str): Error message if not found or failed
    """
    try:
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if user:
            return {
                'success': True,
                'user': user.to_dict()
            }
        else:
            return {
                'success': False,
                'error': f'No user found with phone number {phone_number}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
