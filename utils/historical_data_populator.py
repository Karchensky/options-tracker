#!/usr/bin/env python3
"""
Historical Data Populator
Populates historical options and stock data for the last few weeks to establish baseline.
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import time

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from database.connection import db_manager
from data.data_sources import data_source_manager
from data.ticker_manager import ticker_manager
from core.options_tracker import options_tracker
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

def get_market_days(start_date: date, end_date: date) -> list[date]:
    """Get list of market days (excluding weekends and holidays)."""
    market_days = []
    current_date = start_date
    
    # Load market holidays
    holidays_file = project_root / "us_market_holidays.csv"
    holidays = set()
    if holidays_file.exists():
        holidays_df = pd.read_csv(holidays_file)
        holidays = set(pd.to_datetime(holidays_df['date']).dt.date)
    
    while current_date <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5 and current_date not in holidays:
            market_days.append(current_date)
        current_date += timedelta(days=1)
    
    return market_days

def populate_historical_data(
    start_date: date = None, 
    end_date: date = None,
    symbols: list = None,
    max_symbols: int = 50
) -> bool:
    """
    Populate historical data for the specified date range.
    
    Args:
        start_date: Start date for historical data (default: 3 weeks ago)
        end_date: End date for historical data (default: yesterday)
        symbols: List of symbols to populate (default: S&P 500 top symbols)
        max_symbols: Maximum number of symbols to process
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Set default dates if not provided
        if end_date is None:
            end_date = date.today() - timedelta(days=1)
        if start_date is None:
            start_date = end_date - timedelta(weeks=3)
        
        # Get symbols if not provided
        if symbols is None:
            logger.info("Getting comprehensive ticker list...")
            symbols = ticker_manager.get_comprehensive_ticker_list()
            if not symbols:
                logger.error("Failed to get ticker list")
                return False
            
            # Limit to top symbols for historical population
            symbols = symbols[:max_symbols]
        
        # Get market days
        market_days = get_market_days(start_date, end_date)
        logger.info(f"Populating data for {len(market_days)} market days: {start_date} to {end_date}")
        logger.info(f"Processing {len(symbols)} symbols")
        
        # Initialize database connection
        if not db_manager.test_connection():
            logger.error("Database connection failed")
            return False
        
        total_processed = 0
        total_successful = 0
        
        # Process each market day
        for market_day in market_days:
            logger.info(f"Processing market day: {market_day}")
            
            # Process each symbol
            for symbol in symbols:
                try:
                    # Apply rate limiting
                    rate_limiter.wait_if_needed('polygon')
                    
                    # Check if data already exists for this symbol and date
                    existing_data = options_tracker.session.query(options_tracker.StockPriceSnapshot).filter(
                        options_tracker.StockPriceSnapshot.symbol == symbol,
                        options_tracker.StockPriceSnapshot.snapshot_date == market_day
                    ).first()
                    
                    if existing_data:
                        logger.debug(f"Data already exists for {symbol} on {market_day}, skipping")
                        continue
                    
                    # Get stock price data
                    stock_data = data_source_manager.get_stock_price(symbol, market_day)
                    if stock_data:
                        logger.info(f"Got stock data for {symbol} on {market_day}: ${stock_data.close_price}")
                        # Store stock price data
                        stock_snapshot = options_tracker.StockPriceSnapshot(
                            symbol=symbol,
                            snapshot_date=market_day,
                            close_price=stock_data.close_price,
                            open_price=stock_data.open_price,
                            high_price=stock_data.high_price,
                            low_price=stock_data.low_price,
                            volume=stock_data.volume,
                            data_source='historical_population'
                        )
                        options_tracker.session.add(stock_snapshot)
                        options_tracker.session.commit()
                        logger.debug(f"Stored stock data for {symbol} on {market_day}")
                    else:
                        logger.warning(f"No stock data available for {symbol} on {market_day}")
                    
                    # Get options data for available expirations
                    expirations = data_source_manager.get_available_expirations(symbol)
                    logger.info(f"Processing {len(expirations)} expirations for {symbol}")
                    
                    for expiration in expirations:
                        # Only get options data for expirations that were active on this market day
                        if expiration > market_day:
                            try:
                                logger.info(f"Getting options data for {symbol} expiration {expiration}")
                                options_data = data_source_manager.get_options_data(symbol, expiration)
                                if options_data:
                                    logger.info(f"Got {len(options_data)} options contracts for {symbol} expiration {expiration}")
                                    # Store options data
                                    for option in options_data:
                                        option_record = options_tracker.OptionData(
                                            stock_id=options_tracker._get_or_create_stock_id(symbol),
                                            expiration=option.expiration,
                                            strike=option.strike,
                                            option_type=option.option_type,
                                            last_price=option.last_price,
                                            bid=option.bid,
                                            ask=option.ask,
                                            volume=option.volume,
                                            open_interest=option.open_interest,
                                            implied_volatility=option.implied_volatility,
                                            contract_symbol=option.contract_symbol,
                                            snapshot_date=market_day,
                                            data_source='historical_population'
                                        )
                                        options_tracker.session.add(option_record)
                                    
                                    options_tracker.session.commit()
                                    logger.debug(f"Stored options data for {symbol} expiration {expiration} on {market_day}")
                                else:
                                    logger.warning(f"No options data for {symbol} expiration {expiration}")
                                
                                # Apply rate limiting between API calls
                                logger.info(f"Rate limiting: waiting {config.RATE_LIMIT_DELAY} seconds...")
                                time.sleep(config.RATE_LIMIT_DELAY)
                                
                            except Exception as e:
                                logger.error(f"Error getting options data for {symbol} expiration {expiration}: {e}")
                                continue
                    
                    total_processed += 1
                    total_successful += 1
                    
                    # Progress update every 10 symbols
                    if total_processed % 10 == 0:
                        logger.info(f"Progress: {total_processed}/{len(symbols) * len(market_days)} processed, {total_successful} successful")
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol} on {market_day}: {e}")
                    total_processed += 1
                    continue
        
        logger.info(f"Historical data population completed!")
        logger.info(f"Total processed: {total_processed}")
        logger.info(f"Total successful: {total_successful}")
        logger.info(f"Success rate: {(total_successful/total_processed)*100:.1f}%" if total_processed > 0 else "No data processed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in historical data population: {e}")
        return False

def main():
    """Main function to run historical data population."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('historical_population.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info("Starting historical data population...")
    
    # Calculate date range (last 3 weeks)
    end_date = date.today() - timedelta(days=1)  # Yesterday
    start_date = end_date - timedelta(weeks=3)   # 3 weeks ago
    
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Run historical data population
    success = populate_historical_data(
        start_date=start_date,
        end_date=end_date,
        max_symbols=50  # Start with top 50 symbols
    )
    
    if success:
        logger.info("Historical data population completed successfully!")
        logger.info("You now have baseline data for anomaly detection.")
    else:
        logger.error("Historical data population failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 