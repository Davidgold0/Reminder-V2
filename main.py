import os
import logging
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
load_dotenv()

# Configure logging
def setup_logging():
    """Configure application-wide logging"""
    # Get log level from environment variable, default to INFO for production
    log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add console handler (for Railway logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Log startup message
    root_logger.info(f"Logging initialized at {log_level_name} level")
    
    return root_logger

# Initialize logging
logger = setup_logging()

# Initialize SQLAlchemy (without binding to app yet)
db = SQLAlchemy()


def create_app():
    """
    Application factory function.
    Creates and configures the Flask application.
    """
    app = Flask(__name__)
    
    # Log application startup
    logger.info("Creating Flask application...")
    
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
    
    @app.route('/generate-instances', methods=['POST'])
    def generate_instances_endpoint():
        """API endpoint to trigger instance generation for recurring events"""
        # Import inside function to avoid circular dependency
        from instance_generator import generate_all_instances
        try:
            result = generate_all_instances()
            return result, 200
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/send-reminders', methods=['POST'])
    def send_reminders_endpoint():
        """API endpoint to trigger reminder sending (both initial and escalating)"""
        # Import inside function to avoid circular dependency
        from reminder_sender import main as send_reminders
        try:
            send_reminders()
            return {
                'success': True,
                'message': 'Reminders sent successfully'
            }, 200
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
