#!/usr/bin/env python3
"""
Options Tracker Runner Script
Main entry point for the options tracking system.
"""

import logging
import sys
import os
from datetime import datetime, date
import pytz
import pandas as pd
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from database.connection import db_manager
from data.ticker_manager import ticker_manager
from core.options_tracker import options_tracker
from utils.notifications import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('options_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_market_holidays(target_date: date) -> bool:
    """Check if the target date is a market holiday."""
    try:
        # Load market holidays
        holidays_file = project_root / "us_market_holidays.csv"
        if holidays_file.exists():
            holidays_df = pd.read_csv(holidays_file)
            holiday_dates = set(pd.to_datetime(holidays_df['date']).dt.date)
            return target_date in holiday_dates
        else:
            logger.warning("Market holidays file not found, skipping holiday check")
            return False
    except Exception as e:
        logger.error(f"Error checking market holidays: {e}")
        return False

def check_market_hours() -> bool:
    """Check if it's currently market hours (9:30 AM - 4:00 PM EST)."""
    try:
        # Get current time in US/Eastern
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            logger.info("Weekend detected - markets are closed")
            return False
        
        # Check if it's market hours
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if market_open <= now <= market_close:
            logger.info("Currently during market hours")
            return True
        else:
            logger.info("Outside market hours")
            return False
            
    except Exception as e:
        logger.error(f"Error checking market hours: {e}")
        return False

def update_ticker_list():
    """Update the comprehensive ticker list."""
    try:
        logger.info("Updating ticker list...")
        
        # Get comprehensive ticker list
        symbols = ticker_manager.get_comprehensive_ticker_list()
        
        if symbols:
            # Save to file
            filename = ticker_manager.save_ticker_list(symbols)
            logger.info(f"Updated ticker list saved to {filename}")
            return symbols
        else:
            logger.error("Failed to get ticker list")
            return None
            
    except Exception as e:
        logger.error(f"Error updating ticker list: {e}")
        return None

def test_connections():
    """Test all system connections."""
    logger.info("Testing system connections...")
    
    # Test database connection
    if not db_manager.test_connection():
        logger.error("Database connection failed")
        return False
    
    # Test data source connections
    data_sources = config.get_data_source_priority()
    for source in data_sources:
        if hasattr(options_tracker, '_test_data_source'):
            if not options_tracker._test_data_source(source):
                logger.warning(f"Data source {source} connection failed")
    
    # Test email configuration
    notification_manager = NotificationManager()
    logger.info("Email configuration loaded successfully")
    
    logger.info("All connection tests completed")
    return True

def run_daily_analysis(target_date: date = None, symbols: list = None):
    """Run the daily options analysis."""
    try:
        logger.info("Starting daily options analysis...")
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return False
        
        # Test connections
        if not test_connections():
            logger.error("Connection tests failed")
            return False
        
        # Update ticker list if needed
        if symbols is None:
            symbols = update_ticker_list()
            if not symbols:
                logger.error("Failed to get ticker list")
                return False
        
        # Run analysis
        options_tracker.run_daily_analysis(symbols=symbols, target_date=target_date)
        
        logger.info("Daily analysis completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during daily analysis: {e}")
        
        # Send error alert
        try:
            notification_manager = NotificationManager()
            notification_manager.send_error_alert(str(e), "Daily Analysis")
        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {alert_error}")
        
        return False

def main():
    """Main entry point."""
    logger.info("Options Tracker starting...")
    
    # Get target date (default to today)
    target_date = date.today()
    
    # Check if it's a weekend
    if target_date.weekday() >= 5:
        logger.info(f"Today ({target_date}) is a weekend. Skipping analysis as markets are closed.")
        return
    
    # Check if it's a market holiday
    if check_market_holidays(target_date):
        logger.info(f"Today ({target_date}) is a US market holiday. Skipping analysis as markets are closed.")
        return
    
    # Check if we should run (optional: only during market hours)
    # Uncomment the following lines if you want to restrict to market hours
    # if not check_market_hours():
    #     logger.info("Outside market hours. Skipping analysis.")
    #     return
    
    # Run the analysis
    success = run_daily_analysis(target_date=target_date)
    
    if success:
        logger.info("Options Tracker completed successfully")
    else:
        logger.error("Options Tracker failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 