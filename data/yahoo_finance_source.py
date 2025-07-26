#!/usr/bin/env python3
"""
Yahoo Finance data source for options data.
"""

import requests
import logging
import time
from typing import List, Optional
from datetime import date, datetime
from data.models import OptionsData, StockData
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

class YahooFinanceDataSource:
    """Yahoo Finance data source for options and stock data."""
    
    def __init__(self):
        self.base_url = "https://query2.finance.yahoo.com/v7/finance"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_stock_price(self, symbol: str, target_date: date) -> Optional[StockData]:
        """Get stock price data for a specific date."""
        try:
            # Apply rate limiting
            rate_limiter.wait_if_needed('yahoo_finance')
            
            # Yahoo Finance historical data
            start_timestamp = int(datetime.combine(target_date, datetime.min.time()).timestamp())
            end_timestamp = int(datetime.combine(target_date, datetime.max.time()).timestamp())
            
            url = f"{self.base_url}/chart/{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart']:
                    result = data['chart']['result'][0]
                    if 'timestamp' in result and 'indicators' in result:
                        timestamps = result['timestamp']
                        quotes = result['indicators']['quote'][0]
                        
                        # Find the data for our target date
                        for i, ts in enumerate(timestamps):
                            ts_date = datetime.fromtimestamp(ts).date()
                            if ts_date == target_date:
                                return StockData(
                                    symbol=symbol,
                                    close_price=quotes['close'][i],
                                    open_price=quotes['open'][i],
                                    high_price=quotes['high'][i],
                                    low_price=quotes['low'][i],
                                    volume=quotes['volume'][i]
                                )
            
            return None
            
        except Exception as e:
            logger.error(f"Yahoo Finance stock price error for {symbol}: {e}")
            return None
    
    def get_options_chain(self, symbol: str, expiration_date: date) -> List[OptionsData]:
        """Get options chain for a specific expiration date."""
        try:
            # Apply rate limiting
            rate_limiter.wait_if_needed('yahoo_finance')
            
            # Convert date to timestamp
            expiration_timestamp = int(datetime.combine(expiration_date, datetime.min.time()).timestamp())
            
            url = f"{self.base_url}/options/{symbol}?date={expiration_timestamp}"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'optionChain' in data and 'result' in data['optionChain']:
                    result = data['optionChain']['result'][0]
                    if 'options' in result:
                        options = result['options']
                        options_data = []
                        
                        for option in options:
                            # Process calls
                            if 'calls' in option:
                                for call in option['calls']:
                                    options_data.append(OptionsData(
                                        symbol=symbol,
                                        expiration=expiration_date,
                                        strike=call.get('strike', 0),
                                        option_type='CALL',
                                        last_price=call.get('lastPrice', 0),
                                        bid=call.get('bid', 0),
                                        ask=call.get('ask', 0),
                                        volume=call.get('volume', 0),
                                        open_interest=call.get('openInterest', 0),
                                        implied_volatility=call.get('impliedVolatility', 0),
                                        contract_symbol=call.get('contractSymbol', '')
                                    ))
                            
                            # Process puts
                            if 'puts' in option:
                                for put in option['puts']:
                                    options_data.append(OptionsData(
                                        symbol=symbol,
                                        expiration=expiration_date,
                                        strike=put.get('strike', 0),
                                        option_type='PUT',
                                        last_price=put.get('lastPrice', 0),
                                        bid=put.get('bid', 0),
                                        ask=put.get('ask', 0),
                                        volume=put.get('volume', 0),
                                        open_interest=put.get('openInterest', 0),
                                        implied_volatility=put.get('impliedVolatility', 0),
                                        contract_symbol=put.get('contractSymbol', '')
                                    ))
                        
                        return options_data
            
            return []
            
        except Exception as e:
            logger.error(f"Yahoo Finance options error for {symbol}: {e}")
            return []
    
    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available expiration dates for a symbol."""
        try:
            url = f"{self.base_url}/options/{symbol}"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'optionChain' in data and 'result' in data['optionChain']:
                    result = data['optionChain']['result'][0]
                    if 'expirationDates' in result:
                        expirations = []
                        for timestamp in result['expirationDates']:
                            exp_date = datetime.fromtimestamp(timestamp).date()
                            expirations.append(exp_date)
                        return expirations
            
            return []
            
        except Exception as e:
            logger.error(f"Yahoo Finance expirations error for {symbol}: {e}")
            return []

# Global Yahoo Finance data source
yahoo_finance_source = YahooFinanceDataSource() 