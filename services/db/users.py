from datetime import datetime
from main import db
import logging

# Set up global logger for user database operations
logger = logging.getLogger(__name__)


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

def normalize_phone_number(phone: str) -> list:
    """
    Normalize phone number to multiple possible formats for matching.
    Handles Israeli phone numbers with different formats.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        list: List of possible phone number formats to try
    """
    # Remove common separators
    clean = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    formats = [clean]  # Start with cleaned version
    
    # If it starts with 0 (Israeli local format), try with 972
    if clean.startswith('0'):
        formats.append('972' + clean[1:])
    
    # If it starts with 972, try with leading 0
    if clean.startswith('972'):
        formats.append('0' + clean[3:])
    
    # If it doesn't start with 972 or 0, try both
    if not clean.startswith('972') and not clean.startswith('0'):
        formats.append('972' + clean)
        formats.append('0' + clean)
    
    return formats


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
    logger.info(f"add_user called for phone_number={phone_number}")
    logger.debug(f"User details: first_name={first_name}, last_name={last_name}, "
                 f"timezone={timezone}, language={language}")
    
    try:
        # Check if user with this phone number already exists
        logger.debug(f"Checking for existing user with phone: {phone_number}")
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            logger.warning(f"User with phone {phone_number} already exists (id={existing_user.id})")
            return {
                'success': False,
                'error': f'User with phone number {phone_number} already exists'
            }
        
        # Determine if this is a full registration
        is_registered = all([first_name, last_name, timezone, language])
        logger.debug(f"User registration status will be: {is_registered}")
        
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
        
        logger.info(f"Successfully created user: id={new_user.id}, phone={phone_number}, "
                   f"is_registered={is_registered}")
        
        return {
            'success': True,
            'user': new_user.to_dict()
        }
        
    except Exception as e:
        try:
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed after exception: {rollback_error}")
            db.session.close()
        
        logger.exception(f"Exception in add_user for phone {phone_number}: {str(e)}")
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
    logger.info(f"update_user called for phone_number={phone_number}")
    logger.debug(f"Update fields: first_name={first_name}, last_name={last_name}, "
                 f"timezone={timezone}, language={language}")
    
    try:
        logger.debug(f"Fetching user by phone: {phone_number}")
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if not user:
            logger.warning(f"No user found with phone number {phone_number}")
            return {
                'success': False,
                'error': f'No user found with phone number {phone_number}'
            }
        
        logger.debug(f"User found: id={user.id}, current_is_registered={user.is_registered}")
        
        # Update fields if provided
        updated_fields = []
        if first_name is not None:
            user.first_name = first_name
            updated_fields.append('first_name')
        if last_name is not None:
            user.last_name = last_name
            updated_fields.append('last_name')
        if timezone is not None:
            user.timezone = timezone
            updated_fields.append('timezone')
        if language is not None:
            user.language = language
            updated_fields.append('language')
        
        logger.debug(f"Updated fields: {', '.join(updated_fields) if updated_fields else 'none'}")
        
        # Check if user is now fully registered
        was_registered = user.is_registered
        if user.first_name and user.last_name and user.timezone and user.language:
            user.is_registered = True
        
        db.session.commit()
        
        if not was_registered and user.is_registered:
            logger.info(f"User {phone_number} (id={user.id}) completed registration")
        else:
            logger.info(f"User {phone_number} (id={user.id}) updated successfully")
        
        return {
            'success': True,
            'user': user.to_dict()
        }
        
    except Exception as e:
        try:
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed after exception: {rollback_error}")
            db.session.close()
        
        logger.exception(f"Exception in update_user for phone {phone_number}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_user_by_phone(phone_number):
    """
    Search for a user by phone number. Tries multiple formats to handle
    different phone number representations (with/without country code).
    
    Args:
        phone_number (str): The phone number to search for
    
    Returns:
        dict: Dictionary containing:
            - success (bool): Whether the operation was successful
            - user (dict): User data if found
            - error (str): Error message if not found or failed
    """
    logger.debug(f"get_user_by_phone called for phone_number={phone_number}")
    
    try:
        # Try multiple phone number formats
        phone_formats = normalize_phone_number(phone_number)
        logger.debug(f"Trying phone formats: {phone_formats}")
        
        user = None
        for phone_format in phone_formats:
            user = User.query.filter_by(phone_number=phone_format).first()
            if user:
                logger.debug(f"User found with format '{phone_format}': id={user.id}, is_registered={user.is_registered}")
                break
        
        if user:
            return {
                'success': True,
                'user': user.to_dict()
            }
        else:
            logger.debug(f"No user found with any format of phone number {phone_number}")
            return {
                'success': False,
                'error': f'No user found with phone number {phone_number}'
            }
            
    except Exception as e:
        # Close session on read errors to prevent connection corruption
        try:
            db.session.close()
        except Exception:
            pass
        
        logger.exception(f"Exception in get_user_by_phone for phone {phone_number}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
