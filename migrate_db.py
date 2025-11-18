"""
Database migration script to update schema for partial user registration.
This script drops and recreates all tables with the new schema.
"""
from main import app, db
from services.db.users import User
from services.db.messages import Message
from services.db.events import Event

def migrate_database():
    """
    Drop all existing tables and recreate with new schema.
    WARNING: This will delete all existing data!
    """
    with app.app_context():
        print("🔄 Starting database migration...")
        
        # Drop all tables
        print("🗑️  Dropping existing tables...")
        db.drop_all()
        print("✓ Tables dropped")
        
        # Create all tables with new schema
        print("🏗️  Creating tables with new schema...")
        db.create_all()
        print("✓ Tables created")
        
        print("\n✅ Database migration complete!")
        print("\nNew schema changes:")
        print("  - User.first_name: now nullable")
        print("  - User.last_name: now nullable")
        print("  - User.timezone: now nullable")
        print("  - User.language: now nullable")
        print("  - User.is_registered: new boolean field (default: False)")
        print("\nUsers can now be created with just a phone number!")
        print("Messages are saved for all users, including unregistered ones.")

if __name__ == '__main__':
    print("⚠️  WARNING: This will delete all existing data!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() == 'yes':
        migrate_database()
    else:
        print("❌ Migration cancelled")
