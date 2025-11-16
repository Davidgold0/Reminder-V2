import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
load_dotenv()
# Initialize SQLAlchemy (without binding to app yet)
db = SQLAlchemy()


def create_app():
    """
    Application factory function.
    Creates and configures the Flask application.
    """
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    # Railway provides MYSQL_URL automatically when you add MySQL service
    database_url = os.environ.get('MYSQL_URL')
    if database_url:
        # Railway uses mysql:// but SQLAlchemy 1.4+ requires mysql+pymysql://
        if database_url.startswith('mysql://'):
            database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback for local development
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/reminder_db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Import models (ensures they're registered with SQLAlchemy)
    with app.app_context():
        from services.db.users import User
        from services.db.messages import Message
        from services.db.events import Event
        
        # Setup WhatsApp webhook on app startup (only in production)
        if os.environ.get('WEBHOOK_URL'):
            try:
                from services.messages.whatsapp_webhook import get_webhook_service
                from config import Config
                
                webhook_service = get_webhook_service()
                webhook_url = Config.WEBHOOK_URL
                
                print(f"Setting up WhatsApp webhook: {webhook_url}")
                result = webhook_service.set_webhook_url(webhook_url)
                
                if result['success']:
                    print(f"✓ WhatsApp webhook configured successfully")
                else:
                    print(f"✗ Failed to configure webhook: {result.get('error')}")
            except Exception as e:
                print(f"Warning: Could not setup WhatsApp webhook: {e}")
    
    # Register blueprints and services here when ready
    # Example: app.register_blueprint(some_service_blueprint)
    
    @app.route('/')
    def index():
        return {'message': 'Flask app is running!', 'status': 'success'}
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Webhook endpoint to receive incoming WhatsApp messages from Green API"""
        from services.messages.webhook_handler import handle_webhook
        return handle_webhook()
    
    @app.route('/health')
    def health():
        """Health check endpoint to verify database connection"""
        try:
            # Try to execute a simple query to check DB connection
            db.session.execute(db.text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        return {
            'status': 'healthy',
            'database': db_status
        }
    
    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
