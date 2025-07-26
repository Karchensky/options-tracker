from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, 
    UniqueConstraint, ForeignKey, Index, Text, Numeric
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    """Stock information table with RLS support."""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Numeric(20, 2))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    price_snapshots = relationship("StockPriceSnapshot", back_populates="stock")
    option_data = relationship("OptionData", back_populates="stock")
    anomalies = relationship("OptionAnomaly", back_populates="stock")
    
    __table_args__ = (
        Index('idx_stocks_symbol_active', 'symbol', 'is_active'),
    )

class StockPriceSnapshot(Base):
    """Daily stock price snapshots."""
    __tablename__ = "stock_price_snapshots"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    open_price = Column(Numeric(10, 4))
    high_price = Column(Numeric(10, 4))
    low_price = Column(Numeric(10, 4))
    close_price = Column(Numeric(10, 4), nullable=False)
    volume = Column(Integer)
    data_source = Column(String(50))  # polygon, alpha_vantage, etc.
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    stock = relationship("Stock", back_populates="price_snapshots")
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'snapshot_date', name='uq_stock_price_date'),
        Index('idx_price_snapshot_date', 'snapshot_date'),
        Index('idx_price_snapshot_stock_date', 'stock_id', 'snapshot_date'),
    )

class OptionData(Base):
    """Options data with improved structure."""
    __tablename__ = "option_data"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    contract_symbol = Column(String(50), nullable=False)
    expiration = Column(Date, nullable=False)
    strike = Column(Numeric(10, 4), nullable=False)
    option_type = Column(String(4), nullable=False)  # CALL or PUT
    last_price = Column(Numeric(10, 4))
    bid = Column(Numeric(10, 4))
    ask = Column(Numeric(10, 4))
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    implied_volatility = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    snapshot_date = Column(Date, nullable=False)
    data_source = Column(String(50))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    stock = relationship("Stock", back_populates="option_data")
    
    __table_args__ = (
        UniqueConstraint('contract_symbol', 'snapshot_date', name='uq_option_contract_date'),
        Index('idx_option_data_stock_date', 'stock_id', 'snapshot_date'),
        Index('idx_option_data_expiration', 'expiration'),
        Index('idx_option_data_type', 'option_type'),
    )

class OptionAnomaly(Base):
    """Enhanced anomaly detection results."""
    __tablename__ = "option_anomalies"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    
    # Volume anomalies
    call_volume = Column(Integer, default=0)
    call_volume_baseline = Column(Float)
    call_volume_ratio = Column(Float)
    call_volume_trigger = Column(Boolean, default=False)
    
    put_volume = Column(Integer, default=0)
    put_volume_baseline = Column(Float)
    put_volume_ratio = Column(Float)
    put_volume_trigger = Column(Boolean, default=False)
    
    # Short-term options anomalies
    short_term_call_volume = Column(Integer, default=0)
    short_term_call_baseline = Column(Float)
    short_term_call_ratio = Column(Float)
    short_term_call_trigger = Column(Boolean, default=False)
    
    # OTM options anomalies
    otm_call_volume = Column(Integer, default=0)
    otm_call_baseline = Column(Float)
    otm_call_ratio = Column(Float)
    otm_call_trigger = Column(Boolean, default=False)
    
    # Open Interest anomalies
    call_oi_delta = Column(Integer, default=0)
    call_oi_baseline = Column(Float)
    call_oi_ratio = Column(Float)
    call_oi_trigger = Column(Boolean, default=False)
    
    # Additional anomaly types
    unusual_activity_score = Column(Float)  # Composite score
    insider_probability = Column(Float)  # ML-based probability
    notes = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    stock = relationship("Stock", back_populates="anomalies")
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'snapshot_date', name='uq_anomaly_stock_date'),
        Index('idx_anomaly_date', 'snapshot_date'),
        Index('idx_anomaly_triggers', 'call_volume_trigger', 'put_volume_trigger', 'short_term_call_trigger'),
    )

class DataSourceLog(Base):
    """Log of data source operations for monitoring."""
    __tablename__ = "data_source_logs"
    
    id = Column(Integer, primary_key=True)
    data_source = Column(String(50), nullable=False)
    operation = Column(String(50), nullable=False)  # fetch, store, error
    symbol = Column(String(10))
    status = Column(String(20), nullable=False)  # success, error, partial
    records_processed = Column(Integer, default=0)
    error_message = Column(Text)
    execution_time = Column(Float)  # seconds
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_log_source_date', 'data_source', 'created_at'),
        Index('idx_log_status', 'status'),
    )

class AlertLog(Base):
    """Log of alerts sent for monitoring."""
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)  # email, webhook, etc.
    recipient = Column(String(255))
    subject = Column(String(255))
    content = Column(Text)
    status = Column(String(20), nullable=False)  # sent, failed
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_alert_type_date', 'alert_type', 'created_at'),
        Index('idx_alert_status', 'status'),
    ) 