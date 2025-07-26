import logging
from typing import Dict, List, Optional
from datetime import date, timedelta
from data.data_sources import data_source_manager
from data.yahoo_finance_source import yahoo_finance_source
from data.quandl_source import QuandlDataSource
from config import config

logger = logging.getLogger(__name__)

class DataSourceTester:
    """Test all data sources to ensure they work correctly."""
    
    def __init__(self):
        self.test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
        self.test_date = date.today() - timedelta(days=1)  # Yesterday's data
    
    def test_all_sources(self) -> Dict[str, Dict]:
        """Test all available data sources."""
        results = {}
        
        logger.info("Starting data source testing...")
        
        # Test Polygon.io
        if config.POLYGON_API_KEY:
            results['polygon'] = self._test_polygon()
        
        # Test Alpha Vantage
        if config.ALPHA_VANTAGE_API_KEY:
            results['alpha_vantage'] = self._test_alpha_vantage()
        
        # Test Yahoo Finance
        results['yahoo_finance'] = self._test_yahoo_finance()
        
        # Test Quandl
        if config.QUANDL_API_KEY:
            results['quandl'] = self._test_quandl()
        
        return results
    
    def _test_polygon(self) -> Dict:
        """Test Polygon.io data source."""
        logger.info("Testing Polygon.io...")
        results = {
            'stock_price': {'success': 0, 'failed': 0, 'errors': []},
            'options_data': {'success': 0, 'failed': 0, 'errors': []}
        }
        
        for symbol in self.test_symbols[:2]:  # Test first 2 symbols
            try:
                # Test stock price
                stock_data = data_source_manager.sources['polygon'].get_stock_price(symbol, self.test_date)
                if stock_data and stock_data.close_price > 0:
                    results['stock_price']['success'] += 1
                else:
                    results['stock_price']['failed'] += 1
                    results['stock_price']['errors'].append(f"No stock data for {symbol}")
            except Exception as e:
                results['stock_price']['failed'] += 1
                results['stock_price']['errors'].append(f"Error for {symbol}: {str(e)}")
            
            try:
                # Test options data
                expirations = data_source_manager.sources['polygon'].get_available_expirations(symbol)
                if expirations:
                    options_data = data_source_manager.sources['polygon'].get_options_chain(symbol, expirations[0])
                    if options_data and len(options_data) > 0:
                        results['options_data']['success'] += 1
                    else:
                        results['options_data']['failed'] += 1
                        results['options_data']['errors'].append(f"No options data for {symbol}")
                else:
                    results['options_data']['failed'] += 1
                    results['options_data']['errors'].append(f"No expirations for {symbol}")
            except Exception as e:
                results['options_data']['failed'] += 1
                results['options_data']['errors'].append(f"Error for {symbol}: {str(e)}")
        
        return results
    
    def _test_alpha_vantage(self) -> Dict:
        """Test Alpha Vantage data source."""
        logger.info("Testing Alpha Vantage...")
        results = {
            'stock_price': {'success': 0, 'failed': 0, 'errors': []}
        }
        
        for symbol in self.test_symbols[:2]:
            try:
                stock_data = data_source_manager.sources['alpha_vantage'].get_stock_price(symbol, self.test_date)
                if stock_data and stock_data.close_price > 0:
                    results['stock_price']['success'] += 1
                else:
                    results['stock_price']['failed'] += 1
                    results['stock_price']['errors'].append(f"No stock data for {symbol}")
            except Exception as e:
                results['stock_price']['failed'] += 1
                results['stock_price']['errors'].append(f"Error for {symbol}: {str(e)}")
        
        return results
    
    def _test_yahoo_finance(self) -> Dict:
        """Test Yahoo Finance data source."""
        logger.info("Testing Yahoo Finance...")
        results = {
            'stock_price': {'success': 0, 'failed': 0, 'errors': []},
            'options_data': {'success': 0, 'failed': 0, 'errors': []}
        }
        
        for symbol in self.test_symbols[:2]:
            try:
                # Test stock price
                stock_data = yahoo_finance_source.get_stock_price(symbol, self.test_date)
                if stock_data and stock_data.close_price > 0:
                    results['stock_price']['success'] += 1
                else:
                    results['stock_price']['failed'] += 1
                    results['stock_price']['errors'].append(f"No stock data for {symbol}")
            except Exception as e:
                results['stock_price']['failed'] += 1
                results['stock_price']['errors'].append(f"Error for {symbol}: {str(e)}")
            
            try:
                # Test options data
                expirations = yahoo_finance_source.get_available_expirations(symbol)
                if expirations:
                    options_data = yahoo_finance_source.get_options_chain(symbol, expirations[0])
                    if options_data and len(options_data) > 0:
                        results['options_data']['success'] += 1
                    else:
                        results['options_data']['failed'] += 1
                        results['options_data']['errors'].append(f"No options data for {symbol}")
                else:
                    results['options_data']['failed'] += 1
                    results['options_data']['errors'].append(f"No expirations for {symbol}")
            except Exception as e:
                results['options_data']['failed'] += 1
                results['options_data']['errors'].append(f"Error for {symbol}: {str(e)}")
        
        return results
    
    def _test_quandl(self) -> Dict:
        """Test Quandl data source."""
        logger.info("Testing Quandl...")
        results = {
            'stock_price': {'success': 0, 'failed': 0, 'errors': []}
        }
        
        quandl_source = QuandlDataSource(config.QUANDL_API_KEY)
        
        for symbol in self.test_symbols[:2]:
            try:
                stock_data = quandl_source.get_stock_price(symbol, self.test_date)
                if stock_data and stock_data.close_price > 0:
                    results['stock_price']['success'] += 1
                else:
                    results['stock_price']['failed'] += 1
                    results['stock_price']['errors'].append(f"No stock data for {symbol}")
            except Exception as e:
                results['stock_price']['failed'] += 1
                results['stock_price']['errors'].append(f"Error for {symbol}: {str(e)}")
        
        return results
    
    def generate_report(self, results: Dict[str, Dict]) -> str:
        """Generate a human-readable test report."""
        report = "Data Source Test Report\n"
        report += "=" * 50 + "\n\n"
        
        for source, tests in results.items():
            report += f"{source.upper()}:\n"
            report += "-" * 20 + "\n"
            
            for test_type, result in tests.items():
                total = result['success'] + result['failed']
                success_rate = (result['success'] / total * 100) if total > 0 else 0
                
                report += f"  {test_type}: {result['success']}/{total} ({success_rate:.1f}%)\n"
                
                if result['errors']:
                    report += "  Errors:\n"
                    for error in result['errors'][:3]:  # Show first 3 errors
                        report += f"    - {error}\n"
                    if len(result['errors']) > 3:
                        report += f"    ... and {len(result['errors']) - 3} more errors\n"
            
            report += "\n"
        
        return report
    
    def run_comprehensive_test(self) -> bool:
        """Run comprehensive test and return overall success."""
        results = self.test_all_sources()
        report = self.generate_report(results)
        
        logger.info("Data source test report:\n" + report)
        
        # Check if we have at least one working stock price source
        stock_price_sources = 0
        for source, tests in results.items():
            if 'stock_price' in tests and tests['stock_price']['success'] > 0:
                stock_price_sources += 1
        
        # Check if we have at least one working options data source
        options_sources = 0
        for source, tests in results.items():
            if 'options_data' in tests and tests['options_data']['success'] > 0:
                options_sources += 1
        
        overall_success = stock_price_sources > 0 and options_sources > 0
        
        logger.info(f"Overall test result: {'PASS' if overall_success else 'FAIL'}")
        logger.info(f"Working stock price sources: {stock_price_sources}")
        logger.info(f"Working options data sources: {options_sources}")
        
        return overall_success

# Global tester instance
data_source_tester = DataSourceTester() 