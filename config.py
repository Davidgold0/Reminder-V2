"""
Configuration management for the application.
Loads environment variables for API credentials and settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Database configuration
    MYSQL_URL = os.environ.get('MYSQL_URL')
    
    # Green API (WhatsApp) configuration
    GREEN_API_BASE_URL = os.environ.get('GREEN_API_BASE_URL', 'https://api.green-api.com')
    GREEN_API_INSTANCE_ID = os.environ.get('GREEN_API_INSTANCE_ID')
    GREEN_API_TOKEN = os.environ.get('GREEN_API_TOKEN')
    
    # Webhook configuration
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # Your Railway app URL + /webhook endpoint
    WEBHOOK_TOKEN = os.environ.get('WEBHOOK_TOKEN', 'your_webhook_token_here')
    
    # OpenAI configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    @classmethod
    def validate_green_api_config(cls) -> bool:
        """Validate that Green API credentials are configured"""
        required_configs = {
            'GREEN_API_INSTANCE_ID': cls.GREEN_API_INSTANCE_ID,
            'GREEN_API_TOKEN': cls.GREEN_API_TOKEN
        }
        
        missing_configs = [name for name, value in required_configs.items() if not value]
        
        if missing_configs:
            print("❌ Missing Green API configuration:")
            for config in missing_configs:
                print(f"   - {config}")
            return False
        
        return True
