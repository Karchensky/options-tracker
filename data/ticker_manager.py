import pandas as pd
import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time
from config import config

logger = logging.getLogger(__name__)

class TickerManager:
    """Manages stock ticker lists from multiple sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_sp500_tickers(self) -> List[str]:
        """Get S&P 500 tickers from Wikipedia."""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            
            for table in tables:
                if 'Symbol' in table.columns:
                    symbols = table['Symbol'].str.replace(r'\.', '-', regex=True).tolist()
                    logger.info(f"Retrieved {len(symbols)} S&P 500 tickers")
                    return symbols
            
            return []
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 tickers: {e}")
            return []
    
    def get_sp400_tickers(self) -> List[str]:
        """Get S&P 400 tickers from Wikipedia."""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
            tables = pd.read_html(url)
            
            for table in tables:
                if 'Symbol' in table.columns:
                    symbols = table['Symbol'].str.replace(r'\.', '-', regex=True).tolist()
                    logger.info(f"Retrieved {len(symbols)} S&P 400 tickers")
                    return symbols
            
            return []
        except Exception as e:
            logger.error(f"Failed to fetch S&P 400 tickers: {e}")
            return []
    
    def get_sp600_tickers(self) -> List[str]:
        """Get S&P 600 tickers from Wikipedia."""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
            tables = pd.read_html(url)
            
            for table in tables:
                if 'Symbol' in table.columns:
                    symbols = table['Symbol'].str.replace(r'\.', '-', regex=True).tolist()
                    logger.info(f"Retrieved {len(symbols)} S&P 600 tickers")
                    return symbols
            
            return []
        except Exception as e:
            logger.error(f"Failed to fetch S&P 600 tickers: {e}")
            return []
    
    def get_nasdaq_tickers(self) -> List[str]:
        """Get NASDAQ tickers from NASDAQ website."""
        try:
            # NASDAQ provides a CSV with all listed companies
            url = "https://www.nasdaq.com/market-activity/stocks/screener"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                # Parse the NASDAQ screener page
                tables = pd.read_html(response.text)
                symbols = []
                
                for table in tables:
                    if 'Symbol' in table.columns:
                        symbols.extend(table['Symbol'].tolist())
                
                # Clean symbols
                symbols = [s for s in symbols if isinstance(s, str) and len(s) <= 5]
                logger.info(f"Retrieved {len(symbols)} NASDAQ tickers")
                return symbols
            
            return []
        except Exception as e:
            logger.error(f"Failed to fetch NASDAQ tickers: {e}")
            return []
    
    def get_nyse_tickers(self) -> List[str]:
        """Get NYSE tickers from NYSE website."""
        try:
            # NYSE provides a list of all listed companies
            url = "https://www.nyse.com/listings_directory/stock"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                tables = pd.read_html(response.text)
                symbols = []
                
                for table in tables:
                    if 'Symbol' in table.columns:
                        symbols.extend(table['Symbol'].tolist())
                
                # Clean symbols
                symbols = [s for s in symbols if isinstance(s, str) and len(s) <= 5]
                logger.info(f"Retrieved {len(symbols)} NYSE tickers")
                return symbols
            
            return []
        except Exception as e:
            logger.error(f"Failed to fetch NYSE tickers: {e}")
            return []
    
    def get_polygon_tickers(self) -> List[str]:
        """Get tickers from Polygon.io API (requires API key)."""
        if not config.POLYGON_API_KEY:
            logger.warning("Polygon API key not configured")
            return []
        
        try:
            url = "https://api.polygon.io/v3/reference/tickers"
            params = {
                'apiKey': config.POLYGON_API_KEY,
                'market': 'stocks',
                'active': 'true',
                'limit': 1000
            }
            
            symbols = []
            while True:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    for ticker in results:
                        if ticker.get('type') == 'CS' and ticker.get('active'):
                            symbols.append(ticker['ticker'])
                    
                    # Check for next page
                    next_url = data.get('next_url')
                    if next_url and len(symbols) < 10000:  # Limit to prevent infinite loops
                        url = f"https://api.polygon.io{next_url}"
                        time.sleep(0.1)  # Rate limiting
                    else:
                        break
                else:
                    logger.error(f"Polygon API error: {response.status_code}")
                    break
            
            logger.info(f"Retrieved {len(symbols)} tickers from Polygon")
            return symbols
            
        except Exception as e:
            logger.error(f"Failed to fetch Polygon tickers: {e}")
            return []
    
    def get_comprehensive_ticker_list(self, sources: List[str] = None) -> List[str]:
        """Get comprehensive ticker list from multiple sources."""
        if sources is None:
            sources = ['sp500', 'sp400', 'sp600', 'nasdaq', 'nyse']
        
        all_symbols = set()
        
        source_methods = {
            'sp500': self.get_sp500_tickers,
            'sp400': self.get_sp400_tickers,
            'sp600': self.get_sp600_tickers,
            'nasdaq': self.get_nasdaq_tickers,
            'nyse': self.get_nyse_tickers,
            'polygon': self.get_polygon_tickers
        }
        
        for source in sources:
            if source in source_methods:
                try:
                    symbols = source_methods[source]()
                    all_symbols.update(symbols)
                    logger.info(f"Added {len(symbols)} symbols from {source}")
                    time.sleep(1)  # Rate limiting between sources
                except Exception as e:
                    logger.error(f"Failed to get tickers from {source}: {e}")
        
        # Clean and filter symbols
        cleaned_symbols = []
        for symbol in all_symbols:
            if isinstance(symbol, str) and len(symbol) <= 5 and symbol.isalpha():
                cleaned_symbols.append(symbol.upper())
        
        logger.info(f"Total unique tickers: {len(cleaned_symbols)}")
        return sorted(cleaned_symbols)
    
    def save_ticker_list(self, symbols: List[str], filename: str = "comprehensive_tickers.csv"):
        """Save ticker list to CSV file."""
        try:
            df = pd.DataFrame({
                'Symbol': symbols,
                'Added_Date': datetime.now().date()
            })
            df.to_csv(filename, index=False)
            logger.info(f"Saved {len(symbols)} tickers to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save ticker list: {e}")
            return None
    
    def load_ticker_list(self, filename: str = "comprehensive_tickers.csv") -> List[str]:
        """Load ticker list from CSV file."""
        try:
            df = pd.read_csv(filename)
            symbols = df['Symbol'].tolist()
            logger.info(f"Loaded {len(symbols)} tickers from {filename}")
            return symbols
        except Exception as e:
            logger.error(f"Failed to load ticker list: {e}")
            return []
    
    def filter_active_tickers(self, symbols: List[str], min_market_cap: float = 100000000) -> List[str]:
        """Filter tickers based on market cap and other criteria."""
        # This would require additional API calls to get market cap data
        # For now, return all symbols
        return symbols

# Global ticker manager instance
ticker_manager = TickerManager() 