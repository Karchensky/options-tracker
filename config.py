import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Config:
    """Configuration class for the Options Tracker application."""
    
    # Database Configuration
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
    SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    
    # Email Configuration
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    
    # Data Source Configuration
    # Polygon.io (recommended for options data)
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    
    # Alpha Vantage (backup for stock prices)
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    # Quandl (alternative data source)
    QUANDL_API_KEY = os.getenv("QUANDL_API_KEY")
    
    # Application Settings
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
    RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.1"))
    
    # Anomaly Detection Settings
    VOLUME_THRESHOLD = float(os.getenv("VOLUME_THRESHOLD", "3.0"))  # 3x average volume
    OI_THRESHOLD = float(os.getenv("OI_THRESHOLD", "2.5"))  # 2.5x average OI
    SHORT_TERM_DAYS = int(os.getenv("SHORT_TERM_DAYS", "7"))
    OTM_PERCENTAGE = float(os.getenv("OTM_PERCENTAGE", "10.0"))  # 10% OTM
    
    # Market Hours (EST)
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_HOUR = 16
    MARKET_CLOSE_MINUTE = 0
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required environment variables are set."""
        required_vars = [
            "SUPABASE_DB_URL",
            "SENDER_EMAIL", 
            "EMAIL_PASSWORD",
            "RECIPIENT_EMAIL"
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            print(f"Missing required environment variables: {missing_vars}")
            return False
            
        return True
    
    @classmethod
    def get_data_source_priority(cls) -> list:
        """Return data sources in order of preference."""
        sources = []
        
        if cls.POLYGON_API_KEY:
            sources.append("polygon")
        if cls.ALPHA_VANTAGE_API_KEY:
            sources.append("alpha_vantage")
        if cls.QUANDL_API_KEY:
            sources.append("quandl")
            
        return sources

# Global config instance
config = Config() 