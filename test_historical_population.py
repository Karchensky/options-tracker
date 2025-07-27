#!/usr/bin/env python3
"""
Test Historical Data Population
Quick test to verify historical data population works with a small sample.
"""

import logging
from datetime import date, timedelta
from utils.historical_data_populator import populate_historical_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_historical_population():
    """Test historical data population with a small sample."""
    print("Testing historical data population...")
    
    # Test with just 1 week and 5 symbols
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(weeks=1)
    
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
    
    print(f"Date range: {start_date} to {end_date}")
    print(f"Test symbols: {test_symbols}")
    
    success = populate_historical_data(
        start_date=start_date,
        end_date=end_date,
        symbols=test_symbols
    )
    
    if success:
        print("✅ Historical data population test completed successfully!")
        print("You can now run the full population with: python runner.py --historical")
    else:
        print("❌ Historical data population test failed!")
    
    return success

if __name__ == "__main__":
    test_historical_population() 