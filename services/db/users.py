from datetime import datetime
from main import db


class User(db.Model):
    """User model for storing user information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=True)  # Nullable for partial registration
    last_name = db.Column(db.String(100), nullable=True)  # Nullable for partial registration
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    timezone = db.Column(db.String(50), nullable=True, default='UTC')  # Nullable for partial registration
    language = db.Column(db.String(10), nullable=True, default='en')  # Nullable for partial registration
    is_registered = db.Column(db.Boolean, nullable=False, default=False, index=True)  # Track registration status
    
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
            'is_registered': self.is_registered,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# User Service Functions

def add_user(phone_number, first_name=None, last_name=None, timezone=None, language=None):
    """
    Add a new user to the database. Supports partial registration.
    Can create a user with just phone_number, then update later with full details.
    
    Args:
        phone_number (str): User's phone number (must be unique) - REQUIRED
        first_name (str): User's first name (optional for partial registration)
        last_name (str): User's last name (optional for partial registration)
        timezone (str): User's timezone (optional, default: 'UTC')
        language (str): User's preferred language (optional, default: 'en')
    
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
        
        # Determine if this is a full registration
        is_registered = all([first_name, last_name, timezone, language])
        
        # Create new user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            timezone=timezone or 'UTC',
            language=language or 'en',
            is_registered=is_registered
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


def update_user(phone_number, first_name=None, last_name=None, timezone=None, language=None):
    """
    Update an existing user's information. Used to complete registration.
    
    Args:
        phone_number (str): User's phone number to identify the user
        first_name (str): User's first name (optional)
        last_name (str): User's last name (optional)
        timezone (str): User's timezone (optional)
        language (str): User's preferred language (optional)
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - user (dict): Updated user data if successful
            - error (str): Error message if failed
    """
    try:
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if not user:
            return {
                'success': False,
                'error': f'No user found with phone number {phone_number}'
            }
        
        # Update fields if provided
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if timezone is not None:
            user.timezone = timezone
        if language is not None:
            user.language = language
        
        # Check if user is now fully registered
        if user.first_name and user.last_name and user.timezone and user.language:
            user.is_registered = True
        
        db.session.commit()
        
        return {
            'success': True,
            'user': user.to_dict()
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
