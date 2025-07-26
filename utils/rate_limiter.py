import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API calls with configurable limits per data source."""
    
    def __init__(self):
        # Rate limits per data source (requests per minute)
        self.rate_limits = {
            'polygon': 5,  # 5 requests per minute for Polygon.io
            'alpha_vantage': 5,  # 5 requests per minute for Alpha Vantage
            'yahoo_finance': 2,  # 2 requests per minute for Yahoo Finance
            'quandl': 10,  # 10 requests per minute for Quandl
            'default': 3  # Default rate limit
        }
        
        # Track request timestamps for each data source
        self.request_history = defaultdict(list)
        self.lock = threading.Lock()
    
    def get_rate_limit(self, data_source: str) -> int:
        """Get rate limit for a specific data source."""
        return self.rate_limits.get(data_source, self.rate_limits['default'])
    
    def can_make_request(self, data_source: str) -> bool:
        """Check if a request can be made without exceeding rate limit."""
        with self.lock:
            now = datetime.now()
            rate_limit = self.get_rate_limit(data_source)
            
            # Clean old requests (older than 1 minute)
            cutoff_time = now - timedelta(minutes=1)
            self.request_history[data_source] = [
                timestamp for timestamp in self.request_history[data_source]
                if timestamp > cutoff_time
            ]
            
            # Check if we're under the rate limit
            return len(self.request_history[data_source]) < rate_limit
    
    def wait_if_needed(self, data_source: str) -> float:
        """Wait if necessary to respect rate limits. Returns wait time in seconds."""
        with self.lock:
            if self.can_make_request(data_source):
                # Record the request
                self.request_history[data_source].append(datetime.now())
                return 0.0
            
            # Calculate wait time
            oldest_request = min(self.request_history[data_source])
            wait_until = oldest_request + timedelta(minutes=1)
            wait_time = max(0, (wait_until - datetime.now()).total_seconds())
            
            if wait_time > 0:
                logger.info(f"Rate limit reached for {data_source}, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # Record the request after waiting
            self.request_history[data_source].append(datetime.now())
            return wait_time
    
    def get_status(self, data_source: str) -> Dict:
        """Get current rate limiting status for a data source."""
        with self.lock:
            now = datetime.now()
            cutoff_time = now - timedelta(minutes=1)
            
            # Clean old requests
            self.request_history[data_source] = [
                timestamp for timestamp in self.request_history[data_source]
                if timestamp > cutoff_time
            ]
            
            rate_limit = self.get_rate_limit(data_source)
            current_requests = len(self.request_history[data_source])
            
            return {
                'data_source': data_source,
                'rate_limit': rate_limit,
                'current_requests': current_requests,
                'remaining_requests': max(0, rate_limit - current_requests),
                'can_make_request': current_requests < rate_limit
            }

# Global rate limiter instance
rate_limiter = RateLimiter() 