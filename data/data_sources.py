import requests
import pandas as pd
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from config import config
from data.models import StockData, OptionsData

logger = logging.getLogger(__name__)

class PolygonDataSource:
    """Polygon.io data source for options and stock data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}'
        })
    
    def get_stock_price(self, symbol: str, date: date) -> Optional[StockData]:
        """Get stock price data for a specific date."""
        try:
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{date}/{date}"
            params = {'adjusted': 'true'}
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    result = results[0]
                    return StockData(
                        symbol=symbol,
                        close_price=result['c'],
                        open_price=result['o'],
                        high_price=result['h'],
                        low_price=result['l'],
                        volume=result['v']
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Polygon stock price error for {symbol}: {e}")
            return None
    
    def get_options_chain(self, symbol: str, expiration_date: date) -> List[OptionsData]:
        """Get options chain for a specific expiration date."""
        try:
            url = f"{self.base_url}/v3/reference/options/contracts"
            params = {
                'underlying_ticker': symbol,
                'expiration_date': expiration_date.strftime('%Y-%m-%d'),
                'limit': 1000
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                options_data = []
                for contract in results:
                    # Get detailed options data
                    detailed_data = self._get_option_details(contract['ticker'])
                    if detailed_data:
                        options_data.append(detailed_data)
                
                return options_data
            
            return []
            
        except Exception as e:
            logger.error(f"Polygon options chain error for {symbol}: {e}")
            return []
    
    def _get_option_details(self, contract_ticker: str) -> Optional[OptionsData]:
        """Get detailed options data for a specific contract."""
        try:
            url = f"{self.base_url}/v3/reference/options/contracts/{contract_ticker}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                contract = response.json()['results']
                
                # Get latest trade data
                trade_url = f"{self.base_url}/v3/trades/{contract_ticker}/last"
                trade_response = self.session.get(trade_url, timeout=30)
                
                last_price = None
                volume = 0
                open_interest = 0
                
                if trade_response.status_code == 200:
                    trade_data = trade_response.json()['results']
                    last_price = trade_data.get('p')
                
                # Get open interest
                oi_url = f"{self.base_url}/v3/reference/options/contracts/{contract_ticker}/open-interest"
                oi_response = self.session.get(oi_url, timeout=30)
                
                if oi_response.status_code == 200:
                    oi_data = oi_response.json()['results']
                    open_interest = oi_data.get('open_interest', 0)
                
                return OptionsData(
                    symbol=contract['underlying_ticker'],
                    expiration=datetime.strptime(contract['expiration_date'], '%Y-%m-%d').date(),
                    strike=contract['strike_price'],
                    option_type=contract['contract_type'],
                    last_price=last_price,
                    bid=None,  # Polygon doesn't provide bid/ask in basic tier
                    ask=None,
                    volume=volume,
                    open_interest=open_interest,
                    implied_volatility=None,  # Available in premium tiers
                    contract_symbol=contract_ticker
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Polygon option details error for {contract_ticker}: {e}")
            return None

class AlphaVantageDataSource:
    """Alpha Vantage data source for stock data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.session = requests.Session()
    
    def get_stock_price(self, symbol: str, date: date) -> Optional[StockData]:
        """Get stock price data for a specific date."""
        try:
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'apikey': self.api_key,
                'outputsize': 'compact'
            }
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                time_series = data.get('Time Series (Daily)', {})
                
                date_str = date.strftime('%Y-%m-%d')
                if date_str in time_series:
                    daily_data = time_series[date_str]
                    return StockData(
                        symbol=symbol,
                        close_price=float(daily_data['4. close']),
                        open_price=float(daily_data['1. open']),
                        high_price=float(daily_data['2. high']),
                        low_price=float(daily_data['3. low']),
                        volume=int(daily_data['5. volume'])
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Alpha Vantage stock price error for {symbol}: {e}")
            return None

class DataSourceManager:
    """Manages multiple data sources with fallback mechanisms."""
    
    def __init__(self):
        self.sources = {}
        
        # Initialize available data sources (prioritize Polygon)
        if config.POLYGON_API_KEY:
            self.sources['polygon'] = PolygonDataSource(config.POLYGON_API_KEY)
        
        if config.ALPHA_VANTAGE_API_KEY:
            self.sources['alpha_vantage'] = AlphaVantageDataSource(config.ALPHA_VANTAGE_API_KEY)
        
        # Always add Yahoo Finance as fallback
        from data.yahoo_finance_source import yahoo_finance_source
        self.sources['yahoo_finance'] = yahoo_finance_source
        
        # Add Quandl if API key is available
        if config.QUANDL_API_KEY:
            from data.quandl_source import QuandlDataSource
            self.sources['quandl'] = QuandlDataSource(config.QUANDL_API_KEY)
    
    def get_stock_price(self, symbol: str, target_date: date) -> Optional[StockData]:
        """Get stock price from available sources with fallback."""
        # Try Polygon first (most reliable)
        if 'polygon' in self.sources:
            try:
                logger.info(f"Trying polygon for {symbol} stock price")
                data = self.sources['polygon'].get_stock_price(symbol, target_date)
                if data:
                    logger.info(f"Successfully got stock price from polygon")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting stock price from polygon: {e}")
        
        # Fallback to Alpha Vantage if available
        if 'alpha_vantage' in self.sources:
            try:
                logger.info(f"Trying alpha_vantage for {symbol} stock price")
                data = self.sources['alpha_vantage'].get_stock_price(symbol, target_date)
                if data:
                    logger.info(f"Successfully got stock price from alpha_vantage")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting stock price from alpha_vantage: {e}")
        
        # Fallback to Yahoo Finance
        if 'yahoo_finance' in self.sources:
            try:
                logger.info(f"Trying yahoo_finance for {symbol} stock price")
                data = self.sources['yahoo_finance'].get_stock_price(symbol, target_date)
                if data:
                    logger.info(f"Successfully got stock price from yahoo_finance")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting stock price from yahoo_finance: {e}")
        
        logger.warning(f"Failed to get stock price for {symbol} from all sources")
        return None
    
    def get_options_data(self, symbol: str, expiration_date: date) -> List[OptionsData]:
        """Get options data from available sources."""
        # Try Polygon first (most reliable)
        if 'polygon' in self.sources and hasattr(self.sources['polygon'], 'get_options_chain'):
            try:
                logger.info(f"Trying polygon for {symbol} options")
                data = self.sources['polygon'].get_options_chain(symbol, expiration_date)
                if data and any(opt.volume > 0 or opt.open_interest > 0 for opt in data):
                    logger.info(f"Successfully got options data from polygon")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting options data from polygon: {e}")
        
        # Fallback to Alpha Vantage if available
        if 'alpha_vantage' in self.sources and hasattr(self.sources['alpha_vantage'], 'get_options_chain'):
            try:
                logger.info(f"Trying alpha_vantage for {symbol} options")
                data = self.sources['alpha_vantage'].get_options_chain(symbol, expiration_date)
                if data and any(opt.volume > 0 or opt.open_interest > 0 for opt in data):
                    logger.info(f"Successfully got options data from alpha_vantage")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting options data from alpha_vantage: {e}")
        
        # Fallback to Quandl if available
        if 'quandl' in self.sources and hasattr(self.sources['quandl'], 'get_options_chain'):
            try:
                logger.info(f"Trying quandl for {symbol} options")
                data = self.sources['quandl'].get_options_chain(symbol, expiration_date)
                if data and any(opt.volume > 0 or opt.open_interest > 0 for opt in data):
                    logger.info(f"Successfully got options data from quandl")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting options data from quandl: {e}")
        
        # Fallback to Yahoo Finance
        if 'yahoo_finance' in self.sources and hasattr(self.sources['yahoo_finance'], 'get_options_chain'):
            try:
                logger.info(f"Trying yahoo_finance for {symbol} options")
                data = self.sources['yahoo_finance'].get_options_chain(symbol, expiration_date)
                if data and any(opt.volume > 0 or opt.open_interest > 0 for opt in data):
                    logger.info(f"Successfully got options data from yahoo_finance")
                    return data
                time.sleep(config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"Error getting options data from yahoo_finance: {e}")
        
        logger.warning(f"Failed to get options data for {symbol} from all sources")
        return []
    
    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available expiration dates for a symbol."""
        # This would need to be implemented based on the specific data source
        # For now, return common expiration dates
        today = date.today()
        expirations = []
        
        # Add next few Fridays
        for i in range(1, 9):  # Next 8 weeks
            next_friday = today + timedelta(days=(4 - today.weekday() + 7 * i) % 7)
            expirations.append(next_friday)
        
        # Add monthly expirations
        for i in range(1, 4):  # Next 3 months
            month_date = today.replace(day=1) + timedelta(days=32 * i)
            third_friday = month_date.replace(day=1) + timedelta(days=(4 - month_date.weekday() + 14) % 7)
            expirations.append(third_friday)
        
        return sorted(list(set(expirations)))
    
    def test_connection(self, source_name: str) -> bool:
        """Test connection to a specific data source."""
        if source_name not in self.sources:
            return False
        
        try:
            # Test with a known symbol
            test_symbol = "AAPL"
            test_date = date.today() - timedelta(days=1)
            
            if hasattr(self.sources[source_name], 'get_stock_price'):
                data = self.sources[source_name].get_stock_price(test_symbol, test_date)
                return data is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Connection test failed for {source_name}: {e}")
            return False

# Global data source manager instance
data_source_manager = DataSourceManager() 