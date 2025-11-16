"""
Database initialization script.
Run this to create all database tables.

Usage:
    python init_db.py
"""
from app import create_app, db

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        
        # Print table information
        from services.db.users import User
        from services.db.messages import Message
        from services.db.events import Event
        print(f"\nCreated tables:")
        print(f"  - {User.__tablename__}")
        print(f"  - {Message.__tablename__}")
        print(f"  - {Event.__tablename__}")
