#!/usr/bin/env python3
"""
Data models for options and stock data.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class StockData:
    """Stock price data."""
    symbol: str
    close_price: float
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[int] = None

@dataclass
class OptionsData:
    """Options contract data."""
    symbol: str
    expiration: date
    strike: float
    option_type: str  # 'CALL' or 'PUT'
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    contract_symbol: Optional[str] = None 