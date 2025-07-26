#!/usr/bin/env python3
"""
Mock options data source for testing anomaly detection.
Generates realistic options data when real APIs are not available.
"""

import random
import math
from datetime import date, timedelta
from typing import List, Optional
from dataclasses import dataclass
from data.models import OptionsData, StockData

@dataclass
class MockOptionsData:
    """Mock options data generator."""
    
    def generate_options_data(self, symbol: str, expiration_date: date, stock_price: float) -> List[OptionsData]:
        """Generate realistic options data for testing."""
        
        options_data = []
        
        # Generate strikes around current stock price
        strikes = self._generate_strikes(stock_price)
        
        # Base volume and OI patterns
        base_call_volume = random.randint(100, 1000)
        base_put_volume = random.randint(80, 800)
        base_call_oi = random.randint(500, 5000)
        base_put_oi = random.randint(400, 4000)
        
        # Generate some "anomalous" activity
        anomaly_strikes = random.sample(strikes, min(3, len(strikes)))
        
        for strike in strikes:
            # Determine if this strike has unusual activity
            is_anomalous = strike in anomaly_strikes
            
            # Generate call option
            call_volume = base_call_volume
            call_oi = base_call_oi
            
            if is_anomalous:
                # Create unusual activity
                if random.random() > 0.5:
                    call_volume *= random.uniform(3, 8)  # 3-8x normal volume
                    call_oi *= random.uniform(2, 5)      # 2-5x normal OI
            
            # Add some randomness
            call_volume = int(call_volume * random.uniform(0.5, 1.5))
            call_oi = int(call_oi * random.uniform(0.7, 1.3))
            
            # Calculate realistic option price
            call_price = self._calculate_option_price(stock_price, strike, expiration_date, 'CALL')
            
            call_option = OptionsData(
                symbol=symbol,
                expiration=expiration_date,
                strike=strike,
                option_type='CALL',
                last_price=call_price,
                bid=call_price * 0.98,
                ask=call_price * 1.02,
                volume=call_volume,
                open_interest=call_oi,
                implied_volatility=random.uniform(0.2, 0.6),
                contract_symbol=f"O:{symbol}{expiration_date.strftime('%y%m%d')}C{int(strike*1000):08d}"
            )
            options_data.append(call_option)
            
            # Generate put option
            put_volume = base_put_volume
            put_oi = base_put_oi
            
            if is_anomalous:
                # Create unusual activity
                if random.random() > 0.5:
                    put_volume *= random.uniform(3, 8)  # 3-8x normal volume
                    put_oi *= random.uniform(2, 5)      # 2-5x normal OI
            
            # Add some randomness
            put_volume = int(put_volume * random.uniform(0.5, 1.5))
            put_oi = int(put_oi * random.uniform(0.7, 1.3))
            
            # Calculate realistic option price
            put_price = self._calculate_option_price(stock_price, strike, expiration_date, 'PUT')
            
            put_option = OptionsData(
                symbol=symbol,
                expiration=expiration_date,
                strike=strike,
                option_type='PUT',
                last_price=put_price,
                bid=put_price * 0.98,
                ask=put_price * 1.02,
                volume=put_volume,
                open_interest=put_oi,
                implied_volatility=random.uniform(0.2, 0.6),
                contract_symbol=f"O:{symbol}{expiration_date.strftime('%y%m%d')}P{int(strike*1000):08d}"
            )
            options_data.append(put_option)
        
        return options_data
    
    def _generate_strikes(self, stock_price: float) -> List[float]:
        """Generate realistic strike prices around current stock price."""
        strikes = []
        
        # Generate strikes from 70% to 130% of current price
        min_strike = stock_price * 0.7
        max_strike = stock_price * 1.3
        
        # Generate strikes in $5 increments
        current_strike = min_strike
        while current_strike <= max_strike:
            strikes.append(round(current_strike, 2))
            current_strike += 5
        
        return strikes
    
    def _calculate_option_price(self, stock_price: float, strike: float, expiration: date, option_type: str) -> float:
        """Calculate realistic option price using simplified Black-Scholes approximation."""
        
        # Time to expiration (in years)
        days_to_expiry = (expiration - date.today()).days
        time_to_expiry = max(days_to_expiry / 365, 0.01)
        
        # Simplified option pricing
        if option_type == 'CALL':
            if stock_price > strike:
                # In-the-money call
                intrinsic_value = stock_price - strike
                time_value = max(0.01, intrinsic_value * 0.1 * math.sqrt(time_to_expiry))
                return round(intrinsic_value + time_value, 2)
            else:
                # Out-of-the-money call
                time_value = max(0.01, stock_price * 0.05 * math.sqrt(time_to_expiry))
                return round(time_value, 2)
        else:  # PUT
            if stock_price < strike:
                # In-the-money put
                intrinsic_value = strike - stock_price
                time_value = max(0.01, intrinsic_value * 0.1 * math.sqrt(time_to_expiry))
                return round(intrinsic_value + time_value, 2)
            else:
                # Out-of-the-money put
                time_value = max(0.01, stock_price * 0.05 * math.sqrt(time_to_expiry))
                return round(time_value, 2)

# Global mock data source
mock_options_source = MockOptionsData() 