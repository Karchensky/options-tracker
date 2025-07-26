#!/usr/bin/env python3
"""
Quandl data source for options data.
"""

import requests
import logging
import time
from typing import List, Optional
from datetime import date, datetime
from data.models import OptionsData, StockData
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

class QuandlDataSource:
    """Quandl data source for options and stock data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.quandl.com/api/v3"
        self.session = requests.Session()
    
    def get_stock_price(self, symbol: str, target_date: date) -> Optional[StockData]:
        """Get stock price data for a specific date."""
        try:
            # Apply rate limiting
            rate_limiter.wait_if_needed('quandl')
            
            # Quandl stock data endpoint
            url = f"{self.base_url}/datasets/WIKI/{symbol}/data.json"
            params = {
                'api_key': self.api_key,
                'start_date': target_date.strftime('%Y-%m-%d'),
                'end_date': target_date.strftime('%Y-%m-%d'),
                'order': 'asc'
            }
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'dataset_data' in data and 'data' in data['dataset_data']:
                    rows = data['dataset_data']['data']
                    if rows:
                        row = rows[0]  # First row for the date
                        return StockData(
                            symbol=symbol,
                            close_price=row[4],  # Close price
                            open_price=row[1],   # Open price
                            high_price=row[2],   # High price
                            low_price=row[3],    # Low price
                            volume=row[5]        # Volume
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Quandl stock price error for {symbol}: {e}")
            return None
    
    def get_options_chain(self, symbol: str, expiration_date: date) -> List[OptionsData]:
        """Get options chain for a specific expiration date."""
        try:
            # Quandl options data endpoint
            url = f"{self.base_url}/datasets/OPRA/{symbol}/data.json"
            params = {
                'api_key': self.api_key,
                'start_date': expiration_date.strftime('%Y-%m-%d'),
                'end_date': expiration_date.strftime('%Y-%m-%d'),
                'order': 'asc'
            }
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'dataset_data' in data and 'data' in data['dataset_data']:
                    rows = data['dataset_data']['data']
                    options_data = []
                    
                    for row in rows:
                        # Parse options data from Quandl format
                        # Format: [Date, Strike, Option_Type, Expiration, Volume, Open_Interest, ...]
                        try:
                            options_data.append(OptionsData(
                                symbol=symbol,
                                expiration=expiration_date,
                                strike=float(row[1]),
                                option_type=row[2].upper(),
                                last_price=0.0,  # Not available in Quandl
                                bid=0.0,
                                ask=0.0,
                                volume=int(row[4]) if row[4] else 0,
                                open_interest=int(row[5]) if row[5] else 0,
                                implied_volatility=0.0,
                                contract_symbol=f"{symbol}{expiration_date.strftime('%y%m%d')}{row[2].upper()}{int(float(row[1])*1000):08d}"
                            ))
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Error parsing options row: {e}")
                            continue
                    
                    return options_data
            
            return []
            
        except Exception as e:
            logger.error(f"Quandl options error for {symbol}: {e}")
            return []
    
    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available expiration dates for a symbol."""
        try:
            # Get available dates from Quandl
            url = f"{self.base_url}/datasets/OPRA/{symbol}/data.json"
            params = {
                'api_key': self.api_key,
                'limit': 1000,
                'order': 'desc'
            }
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'dataset_data' in data and 'data' in data['dataset_data']:
                    rows = data['dataset_data']['data']
                    expirations = set()
                    
                    for row in rows:
                        try:
                            exp_date = datetime.strptime(row[3], '%Y-%m-%d').date()
                            expirations.add(exp_date)
                        except (ValueError, IndexError):
                            continue
                    
                    return sorted(list(expirations))
            
            return []
            
        except Exception as e:
            logger.error(f"Quandl expirations error for {symbol}: {e}")
            return []

# Global Quandl data source (will be initialized with API key)
quandl_source = None 