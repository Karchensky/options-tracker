import logging
import time
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session

from config import config
from database.connection import db_manager
from database.models import Stock, StockPriceSnapshot, OptionData, OptionAnomaly, DataSourceLog, AlertLog
from data.ticker_manager import ticker_manager
from data.data_sources import data_source_manager
from analysis.anomaly_detector import anomaly_detector
from utils.notifications import NotificationManager

logger = logging.getLogger(__name__)

class OptionsTracker:
    """Main options tracking system with improved architecture."""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
        self.session = None
    
    def run_daily_analysis(self, symbols: List[str] = None, target_date: date = None):
        """Run daily options analysis for all symbols."""
        if target_date is None:
            target_date = date.today()
        
        if symbols is None:
            symbols = ticker_manager.load_ticker_list()
        
        logger.info(f"Starting daily analysis for {len(symbols)} symbols on {target_date}")
        
        start_time = time.time()
        processed_count = 0
        error_count = 0
        
        with db_manager.get_session() as session:
            self.session = session
            
            for i, symbol in enumerate(symbols):
                try:
                    logger.info(f"Processing {symbol} ({i+1}/{len(symbols)})")
                    
                    # Process single symbol
                    success = self._process_symbol(symbol, target_date)
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                    
                    # Rate limiting
                    time.sleep(config.RATE_LIMIT_DELAY)
                    
                    # Log progress every 100 symbols
                    if (i + 1) % 100 == 0:
                        logger.info(f"Progress: {i+1}/{len(symbols)} symbols processed")
                
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    error_count += 1
                    self._log_data_source_error("options_tracker", "process_symbol", symbol, str(e))
            
            # Detect anomalies for all processed symbols
            self._detect_anomalies_for_date(target_date)
            
            # Send alerts
            self._send_daily_alerts(target_date)
        
        execution_time = time.time() - start_time
        logger.info(f"Daily analysis completed in {execution_time:.2f}s")
        logger.info(f"Processed: {processed_count}, Errors: {error_count}")
        
        # Log completion
        self._log_data_source_success("options_tracker", "daily_analysis", 
                                    records_processed=processed_count,
                                    execution_time=execution_time)
    
    def _process_symbol(self, symbol: str, target_date: date) -> bool:
        """Process a single symbol's options data."""
        try:
            # Get or create stock record
            stock = self._get_or_create_stock(symbol)
            
            # Get stock price
            stock_data = data_source_manager.get_stock_price(symbol, target_date)
            if not stock_data:
                logger.warning(f"No stock price data for {symbol}")
                return False
            
            # Store stock price snapshot
            self._store_stock_price(stock, stock_data, target_date)
            
            # Get available expiration dates
            expirations = data_source_manager.get_available_expirations(symbol)
            
            # Process options data for each expiration
            for expiration in expirations:
                options_data = data_source_manager.get_options_data(symbol, expiration)
                if options_data:
                    self._store_options_data(stock, options_data, target_date)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")
            return False
    
    def _get_or_create_stock(self, symbol: str) -> Stock:
        """Get or create a stock record."""
        stock = self.session.query(Stock).filter_by(symbol=symbol).first()
        
        if not stock:
            stock = Stock(
                symbol=symbol,
                is_active=True
            )
            self.session.add(stock)
            self.session.flush()  # Get the ID
        
        return stock
    
    def _store_stock_price(self, stock: Stock, stock_data, target_date: date):
        """Store stock price snapshot."""
        # Check if we already have data for this date
        existing = self.session.query(StockPriceSnapshot).filter_by(
            stock_id=stock.id,
            snapshot_date=target_date
        ).first()
        
        if existing:
            # Update existing record
            existing.close_price = stock_data.close_price
            existing.open_price = stock_data.open_price
            existing.high_price = stock_data.high_price
            existing.low_price = stock_data.low_price
            existing.volume = stock_data.volume
            existing.data_source = "polygon"  # or get from stock_data
        else:
            # Create new record
            snapshot = StockPriceSnapshot(
                stock_id=stock.id,
                snapshot_date=target_date,
                close_price=stock_data.close_price,
                open_price=stock_data.open_price,
                high_price=stock_data.high_price,
                low_price=stock_data.low_price,
                volume=stock_data.volume,
                data_source="polygon"  # or get from stock_data
            )
            self.session.add(snapshot)
    
    def _store_options_data(self, stock: Stock, options_data: List, target_date: date):
        """Store options data."""
        for option in options_data:
            # Check if we already have this contract for this date
            existing = self.session.query(OptionData).filter_by(
                contract_symbol=option.contract_symbol,
                snapshot_date=target_date
            ).first()
            
            if existing:
                # Update existing record
                existing.last_price = option.last_price
                existing.bid = option.bid
                existing.ask = option.ask
                existing.volume = option.volume
                existing.open_interest = option.open_interest
                existing.implied_volatility = option.implied_volatility
                existing.delta = option.delta
                existing.gamma = option.gamma
                existing.theta = option.theta
                existing.vega = option.vega
                existing.data_source = "polygon"  # or get from option
            else:
                # Create new record
                option_record = OptionData(
                    stock_id=stock.id,
                    contract_symbol=option.contract_symbol,
                    expiration=option.expiration,
                    strike=option.strike,
                    option_type=option.option_type,
                    last_price=option.last_price,
                    bid=option.bid,
                    ask=option.ask,
                    volume=option.volume,
                    open_interest=option.open_interest,
                    implied_volatility=option.implied_volatility,
                    delta=option.delta,
                    gamma=option.gamma,
                    theta=option.theta,
                    vega=option.vega,
                    snapshot_date=target_date,
                    data_source="polygon"  # or get from option
                )
                self.session.add(option_record)
    
    def _detect_anomalies_for_date(self, target_date: date):
        """Detect anomalies for all symbols on a given date."""
        logger.info(f"Detecting anomalies for {target_date}")
        
        # Get all stocks with data for this date
        stocks_with_data = self.session.query(Stock).join(StockPriceSnapshot).filter(
            StockPriceSnapshot.snapshot_date == target_date
        ).all()
        
        for stock in stocks_with_data:
            try:
                # Get stock price
                price_snapshot = self.session.query(StockPriceSnapshot).filter_by(
                    stock_id=stock.id,
                    snapshot_date=target_date
                ).first()
                
                if not price_snapshot:
                    continue
                
                # Get options data for this date
                options_data = self.session.query(OptionData).filter_by(
                    stock_id=stock.id,
                    snapshot_date=target_date
                ).all()
                
                # Get historical data for baseline calculation
                historical_data = self._get_historical_data(stock.id, target_date)
                
                # Detect anomalies
                anomaly_result = anomaly_detector.detect_anomalies(
                    stock.symbol,
                    target_date,
                    options_data,
                    price_snapshot.close_price,
                    historical_data
                )
                
                # Store anomaly result
                self._store_anomaly_result(stock, anomaly_result)
                
            except Exception as e:
                logger.error(f"Error detecting anomalies for {stock.symbol}: {e}")
    
    def _get_historical_data(self, stock_id: int, target_date: date, days: int = 14) -> pd.DataFrame:
        """Get historical options data for baseline calculation."""
        start_date = target_date - timedelta(days=days)
        
        query = self.session.query(OptionData).filter(
            OptionData.stock_id == stock_id,
            OptionData.snapshot_date >= start_date,
            OptionData.snapshot_date < target_date
        )
        
        results = query.all()
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for result in results:
            data.append({
                'expiration': result.expiration,
                'strike': result.strike,
                'option_type': result.option_type,
                'volume': result.volume,
                'open_interest': result.open_interest,
                'snapshot_date': result.snapshot_date
            })
        
        return pd.DataFrame(data)
    
    def _store_anomaly_result(self, stock: Stock, anomaly_result):
        """Store anomaly detection result."""
        # Check if we already have an anomaly record for this date
        existing = self.session.query(OptionAnomaly).filter_by(
            stock_id=stock.id,
            snapshot_date=anomaly_result.snapshot_date
        ).first()
        
        if existing:
            # Update existing record
            existing.call_volume = anomaly_result.call_volume
            existing.call_volume_baseline = anomaly_result.call_volume_baseline
            existing.call_volume_ratio = anomaly_result.call_volume_ratio
            existing.call_volume_trigger = anomaly_result.call_volume_trigger
            existing.put_volume = anomaly_result.put_volume
            existing.put_volume_baseline = anomaly_result.put_volume_baseline
            existing.put_volume_ratio = anomaly_result.put_volume_ratio
            existing.put_volume_trigger = anomaly_result.put_volume_trigger
            existing.short_term_call_volume = anomaly_result.short_term_call_volume
            existing.short_term_call_baseline = anomaly_result.short_term_call_baseline
            existing.short_term_call_ratio = anomaly_result.short_term_call_ratio
            existing.short_term_call_trigger = anomaly_result.short_term_call_trigger
            existing.otm_call_volume = anomaly_result.otm_call_volume
            existing.otm_call_baseline = anomaly_result.otm_call_baseline
            existing.otm_call_ratio = anomaly_result.otm_call_ratio
            existing.otm_call_trigger = anomaly_result.otm_call_trigger
            existing.call_oi_delta = anomaly_result.call_oi_delta
            existing.call_oi_baseline = anomaly_result.call_oi_baseline
            existing.call_oi_ratio = anomaly_result.call_oi_ratio
            existing.call_oi_trigger = anomaly_result.call_oi_trigger
            existing.unusual_activity_score = anomaly_result.unusual_activity_score
            existing.insider_probability = anomaly_result.insider_probability
            existing.notes = anomaly_result.notes
        else:
            # Create new record
            anomaly = OptionAnomaly(
                stock_id=stock.id,
                snapshot_date=anomaly_result.snapshot_date,
                call_volume=anomaly_result.call_volume,
                call_volume_baseline=anomaly_result.call_volume_baseline,
                call_volume_ratio=anomaly_result.call_volume_ratio,
                call_volume_trigger=anomaly_result.call_volume_trigger,
                put_volume=anomaly_result.put_volume,
                put_volume_baseline=anomaly_result.put_volume_baseline,
                put_volume_ratio=anomaly_result.put_volume_ratio,
                put_volume_trigger=anomaly_result.put_volume_trigger,
                short_term_call_volume=anomaly_result.short_term_call_volume,
                short_term_call_baseline=anomaly_result.short_term_call_baseline,
                short_term_call_ratio=anomaly_result.short_term_call_ratio,
                short_term_call_trigger=anomaly_result.short_term_call_trigger,
                otm_call_volume=anomaly_result.otm_call_volume,
                otm_call_baseline=anomaly_result.otm_call_baseline,
                otm_call_ratio=anomaly_result.otm_call_ratio,
                otm_call_trigger=anomaly_result.otm_call_trigger,
                call_oi_delta=anomaly_result.call_oi_delta,
                call_oi_baseline=anomaly_result.call_oi_baseline,
                call_oi_ratio=anomaly_result.call_oi_ratio,
                call_oi_trigger=anomaly_result.call_oi_trigger,
                unusual_activity_score=anomaly_result.unusual_activity_score,
                insider_probability=anomaly_result.insider_probability,
                notes=anomaly_result.notes
            )
            self.session.add(anomaly)
    
    def _send_daily_alerts(self, target_date: date):
        """Send daily anomaly alerts."""
        # Get all anomalies for this date
        anomalies = self.session.query(OptionAnomaly).join(Stock).filter(
            OptionAnomaly.snapshot_date == target_date,
            (OptionAnomaly.call_volume_trigger == True) |
            (OptionAnomaly.put_volume_trigger == True) |
            (OptionAnomaly.short_term_call_trigger == True) |
            (OptionAnomaly.otm_call_trigger == True) |
            (OptionAnomaly.call_oi_trigger == True)
        ).all()
        
        if anomalies:
            # Send email alert
            self.notification_manager.send_anomaly_alert(anomalies, target_date)
            logger.info(f"Sent alerts for {len(anomalies)} anomalies")
        else:
            logger.info("No anomalies detected for today")
    
    def _log_data_source_success(self, data_source: str, operation: str, 
                                records_processed: int = 0, execution_time: float = 0):
        """Log successful data source operation."""
        log = DataSourceLog(
            data_source=data_source,
            operation=operation,
            status="success",
            records_processed=records_processed,
            execution_time=execution_time
        )
        self.session.add(log)
    
    def _log_data_source_error(self, data_source: str, operation: str, 
                              symbol: str, error_message: str):
        """Log data source error."""
        log = DataSourceLog(
            data_source=data_source,
            operation=operation,
            symbol=symbol,
            status="error",
            error_message=error_message
        )
        self.session.add(log)

# Global options tracker instance
options_tracker = OptionsTracker() 