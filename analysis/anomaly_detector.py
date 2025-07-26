import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from config import config

logger = logging.getLogger(__name__)

@dataclass
class AnomalyResult:
    """Result of anomaly detection analysis."""
    symbol: str
    snapshot_date: date
    
    # Volume anomalies
    call_volume: int
    call_volume_baseline: float
    call_volume_ratio: float
    call_volume_trigger: bool
    
    put_volume: int
    put_volume_baseline: float
    put_volume_ratio: float
    put_volume_trigger: bool
    
    # Short-term options anomalies
    short_term_call_volume: int
    short_term_call_baseline: float
    short_term_call_ratio: float
    short_term_call_trigger: bool
    
    # OTM options anomalies
    otm_call_volume: int
    otm_call_baseline: float
    otm_call_ratio: float
    otm_call_trigger: bool
    
    # Open Interest anomalies
    call_oi_delta: int
    call_oi_baseline: float
    call_oi_ratio: float
    call_oi_trigger: bool
    
    # Additional metrics
    unusual_activity_score: float
    insider_probability: float
    notes: str

class AnomalyDetector:
    """Enhanced anomaly detection for options trading."""
    
    def __init__(self):
        self.volume_threshold = config.VOLUME_THRESHOLD
        self.oi_threshold = config.OI_THRESHOLD
        self.short_term_days = config.SHORT_TERM_DAYS
        self.otm_percentage = config.OTM_PERCENTAGE
        
        # Initialize ML models with better parameters for options data
        self.isolation_forest = IsolationForest(
            contamination=0.05,  # Lower contamination for more precise detection
            random_state=42,
            n_estimators=100,  # More trees for better accuracy
            max_samples='auto'
        )
        self.scaler = StandardScaler()
        
        # Additional parameters for options-specific detection
        self.min_data_points = 5  # Minimum data points needed for baseline
        self.volume_weight = 0.4   # Weight for volume anomalies
        self.oi_weight = 0.3       # Weight for open interest anomalies
        self.short_term_weight = 0.2  # Weight for short-term anomalies
        self.otm_weight = 0.1      # Weight for OTM anomalies
    
    def detect_anomalies(self, symbol: str, snapshot_date: date, 
                        options_data: List, stock_price: float,
                        historical_data: pd.DataFrame) -> AnomalyResult:
        """Detect anomalies in options trading activity."""
        
        # Convert options data to DataFrame for easier analysis
        df = pd.DataFrame([{
            'expiration': opt.expiration,
            'strike': opt.strike,
            'option_type': opt.option_type,
            'volume': opt.volume,
            'open_interest': opt.open_interest,
            'implied_volatility': opt.implied_volatility
        } for opt in options_data])
        
        if df.empty:
            return self._create_empty_result(symbol, snapshot_date)
        
        # Calculate various anomaly metrics
        volume_anomalies = self._detect_volume_anomalies(df, historical_data, stock_price)
        short_term_anomalies = self._detect_short_term_anomalies(df, historical_data, stock_price)
        otm_anomalies = self._detect_otm_anomalies(df, historical_data, stock_price)
        oi_anomalies = self._detect_oi_anomalies(df, historical_data)
        
        # Calculate composite scores
        unusual_activity_score = self._calculate_unusual_activity_score(
            volume_anomalies, short_term_anomalies, otm_anomalies, oi_anomalies
        )
        
        insider_probability = self._calculate_insider_probability(
            volume_anomalies, short_term_anomalies, otm_anomalies, oi_anomalies
        )
        
        # Generate notes
        notes = self._generate_anomaly_notes(
            volume_anomalies, short_term_anomalies, otm_anomalies, oi_anomalies
        )
        
        return AnomalyResult(
            symbol=symbol,
            snapshot_date=snapshot_date,
            **volume_anomalies,
            **short_term_anomalies,
            **otm_anomalies,
            **oi_anomalies,
            unusual_activity_score=unusual_activity_score,
            insider_probability=insider_probability,
            notes=notes
        )
    
    def _detect_volume_anomalies(self, df: pd.DataFrame, historical_data: pd.DataFrame, 
                                stock_price: float) -> Dict:
        """Detect volume anomalies for calls and puts."""
        
        # Calculate today's volumes (convert numpy.int64 to regular int)
        call_volume = int(df[df['option_type'] == 'CALL']['volume'].sum())
        put_volume = int(df[df['option_type'] == 'PUT']['volume'].sum())
        
        # Calculate baselines from historical data
        call_baseline = self._calculate_volume_baseline(historical_data, 'CALL')
        put_baseline = self._calculate_volume_baseline(historical_data, 'PUT')
        
        # Calculate ratios
        call_ratio = call_volume / call_baseline if call_baseline > 0 else 0
        put_ratio = put_volume / put_baseline if put_baseline > 0 else 0
        
        return {
            'call_volume': call_volume,
            'call_volume_baseline': call_baseline,
            'call_volume_ratio': call_ratio,
            'call_volume_trigger': call_ratio > self.volume_threshold,
            'put_volume': put_volume,
            'put_volume_baseline': put_baseline,
            'put_volume_ratio': put_ratio,
            'put_volume_trigger': put_ratio > self.volume_threshold
        }
    
    def _detect_short_term_anomalies(self, df: pd.DataFrame, historical_data: pd.DataFrame,
                                   stock_price: float) -> Dict:
        """Detect anomalies in short-term options."""
        
        # Filter for short-term options
        short_term_date = date.today() + timedelta(days=self.short_term_days)
        short_term_df = df[df['expiration'] <= short_term_date]
        
        short_term_call_volume = int(short_term_df[short_term_df['option_type'] == 'CALL']['volume'].sum())
        
        # Calculate baseline for short-term calls
        short_term_baseline = self._calculate_short_term_baseline(historical_data, 'CALL')
        
        short_term_ratio = short_term_call_volume / short_term_baseline if short_term_baseline > 0 else 0
        
        return {
            'short_term_call_volume': short_term_call_volume,
            'short_term_call_baseline': short_term_baseline,
            'short_term_call_ratio': short_term_ratio,
            'short_term_call_trigger': short_term_ratio > self.volume_threshold
        }
    
    def _detect_otm_anomalies(self, df: pd.DataFrame, historical_data: pd.DataFrame,
                             stock_price: float) -> Dict:
        """Detect anomalies in out-of-the-money options."""
        
        # Filter for OTM calls
        otm_threshold = stock_price * (1 + self.otm_percentage / 100)
        otm_df = df[(df['option_type'] == 'CALL') & (df['strike'] > otm_threshold)]
        
        otm_call_volume = int(otm_df['volume'].sum())
        
        # Calculate baseline for OTM calls
        otm_baseline = self._calculate_otm_baseline(historical_data, stock_price)
        
        otm_ratio = otm_call_volume / otm_baseline if otm_baseline > 0 else 0
        
        return {
            'otm_call_volume': otm_call_volume,
            'otm_call_baseline': otm_baseline,
            'otm_call_ratio': otm_ratio,
            'otm_call_trigger': otm_ratio > self.volume_threshold
        }
    
    def _detect_oi_anomalies(self, df: pd.DataFrame, historical_data: pd.DataFrame) -> Dict:
        """Detect open interest anomalies."""
        
        # Calculate today's OI delta
        call_oi = df[df['option_type'] == 'CALL']['open_interest'].sum()
        put_oi = df[df['option_type'] == 'PUT']['open_interest'].sum()
        call_oi_delta = int(call_oi - put_oi)
        
        # Calculate baseline OI delta
        oi_baseline = self._calculate_oi_baseline(historical_data)
        
        oi_ratio = abs(call_oi_delta) / abs(oi_baseline) if abs(oi_baseline) > 0 else 0
        
        return {
            'call_oi_delta': call_oi_delta,
            'call_oi_baseline': oi_baseline,
            'call_oi_ratio': oi_ratio,
            'call_oi_trigger': oi_ratio > self.oi_threshold
        }
    
    def _calculate_volume_baseline(self, historical_data: pd.DataFrame, option_type: str) -> float:
        """Calculate baseline volume from historical data with outlier removal."""
        if historical_data.empty:
            return 0.0
        
        # Filter for option type
        type_data = historical_data[historical_data['option_type'] == option_type]
        if type_data.empty or len(type_data) < self.min_data_points:
            return 0.0
        
        # Remove outliers using IQR method
        Q1 = type_data['volume'].quantile(0.25)
        Q3 = type_data['volume'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        filtered_data = type_data[
            (type_data['volume'] >= lower_bound) & 
            (type_data['volume'] <= upper_bound)
        ]
        
        if filtered_data.empty:
            return type_data['volume'].median()
        
        # Calculate median volume (more robust than mean)
        return filtered_data['volume'].median()
    
    def _calculate_short_term_baseline(self, historical_data: pd.DataFrame, option_type: str) -> float:
        """Calculate baseline for short-term options."""
        if historical_data.empty:
            return 0
        
        # Filter for short-term options
        short_term_date = date.today() + timedelta(days=self.short_term_days)
        short_term_data = historical_data[
            (historical_data['option_type'] == option_type) &
            (historical_data['expiration'] <= short_term_date)
        ]
        
        return short_term_data['volume'].mean() if not short_term_data.empty else 0
    
    def _calculate_otm_baseline(self, historical_data: pd.DataFrame, stock_price: float) -> float:
        """Calculate baseline for OTM options."""
        if historical_data.empty:
            return 0
        
        # Filter for OTM calls
        otm_threshold = stock_price * (1 + self.otm_percentage / 100)
        otm_data = historical_data[
            (historical_data['option_type'] == 'CALL') &
            (historical_data['strike'] > otm_threshold)
        ]
        
        return otm_data['volume'].mean() if not otm_data.empty else 0
    
    def _calculate_oi_baseline(self, historical_data: pd.DataFrame) -> float:
        """Calculate baseline OI delta."""
        if historical_data.empty:
            return 0
        
        # Calculate OI delta for each date
        oi_deltas = []
        for date in historical_data['snapshot_date'].unique():
            date_data = historical_data[historical_data['snapshot_date'] == date]
            call_oi = date_data[date_data['option_type'] == 'CALL']['open_interest'].sum()
            put_oi = date_data[date_data['option_type'] == 'PUT']['open_interest'].sum()
            oi_deltas.append(call_oi - put_oi)
        
        return np.mean(oi_deltas) if oi_deltas else 0
    
    def _calculate_unusual_activity_score(self, volume_anomalies: Dict, 
                                        short_term_anomalies: Dict,
                                        otm_anomalies: Dict, oi_anomalies: Dict) -> float:
        """Calculate composite unusual activity score."""
        
        scores = []
        
        # Volume scores
        if volume_anomalies['call_volume_trigger']:
            scores.append(min(volume_anomalies['call_volume_ratio'] / self.volume_threshold, 3.0))
        if volume_anomalies['put_volume_trigger']:
            scores.append(min(volume_anomalies['put_volume_ratio'] / self.volume_threshold, 3.0))
        
        # Short-term scores
        if short_term_anomalies['short_term_call_trigger']:
            scores.append(min(short_term_anomalies['short_term_call_ratio'] / self.volume_threshold, 3.0))
        
        # OTM scores
        if otm_anomalies['otm_call_trigger']:
            scores.append(min(otm_anomalies['otm_call_ratio'] / self.volume_threshold, 3.0))
        
        # OI scores
        if oi_anomalies['call_oi_trigger']:
            scores.append(min(oi_anomalies['call_oi_ratio'] / self.oi_threshold, 3.0))
        
        return np.mean(scores) if scores else 0.0
    
    def _calculate_insider_probability(self, volume_anomalies: Dict,
                                     short_term_anomalies: Dict,
                                     otm_anomalies: Dict, oi_anomalies: Dict) -> float:
        """Calculate probability of insider trading based on anomalies."""
        
        # Weighted scoring system based on different anomaly types
        score = 0.0
        
        # Volume anomalies (40% weight)
        if volume_anomalies['call_volume_trigger']:
            score += self.volume_weight * min(volume_anomalies['call_volume_ratio'] / self.volume_threshold, 2.0)
        if volume_anomalies['put_volume_trigger']:
            score += self.volume_weight * min(volume_anomalies['put_volume_ratio'] / self.volume_threshold, 2.0)
        
        # Open Interest anomalies (30% weight)
        if oi_anomalies['call_oi_trigger']:
            score += self.oi_weight * min(oi_anomalies['call_oi_ratio'] / self.oi_threshold, 2.0)
        
        # Short-term anomalies (20% weight)
        if short_term_anomalies['short_term_call_trigger']:
            score += self.short_term_weight * min(short_term_anomalies['short_term_call_ratio'] / self.volume_threshold, 2.0)
        
        # OTM anomalies (10% weight)
        if otm_anomalies['otm_call_trigger']:
            score += self.otm_weight * min(otm_anomalies['otm_call_ratio'] / self.volume_threshold, 2.0)
        
        # Convert score to probability (0-1 range)
        probability = min(score, 1.0)
        
        # Base probability from volume anomalies
        if volume_anomalies['call_volume_trigger']:
            probability += 0.2
        if volume_anomalies['put_volume_trigger']:
            probability += 0.2
        
        # Short-term options are more suspicious
        if short_term_anomalies['short_term_call_trigger']:
            probability += 0.3
        
        # OTM options are very suspicious
        if otm_anomalies['otm_call_trigger']:
            probability += 0.4
        
        # OI changes can indicate accumulation
        if oi_anomalies['call_oi_trigger']:
            probability += 0.1
        
        return min(probability, 1.0)
    
    def _generate_anomaly_notes(self, volume_anomalies: Dict,
                              short_term_anomalies: Dict,
                              otm_anomalies: Dict, oi_anomalies: Dict) -> str:
        """Generate human-readable notes about detected anomalies."""
        
        notes = []
        
        if volume_anomalies['call_volume_trigger']:
            notes.append(f"Call volume {volume_anomalies['call_volume_ratio']:.1f}x normal")
        
        if volume_anomalies['put_volume_trigger']:
            notes.append(f"Put volume {volume_anomalies['put_volume_ratio']:.1f}x normal")
        
        if short_term_anomalies['short_term_call_trigger']:
            notes.append(f"Short-term call volume {short_term_anomalies['short_term_call_ratio']:.1f}x normal")
        
        if otm_anomalies['otm_call_trigger']:
            notes.append(f"OTM call volume {otm_anomalies['otm_call_ratio']:.1f}x normal")
        
        if oi_anomalies['call_oi_trigger']:
            notes.append(f"Unusual OI change: {oi_anomalies['call_oi_ratio']:.1f}x normal")
        
        return "; ".join(notes) if notes else "No significant anomalies detected"
    
    def _create_empty_result(self, symbol: str, snapshot_date: date) -> AnomalyResult:
        """Create empty result when no data is available."""
        return AnomalyResult(
            symbol=symbol,
            snapshot_date=snapshot_date,
            call_volume=0, call_volume_baseline=0, call_volume_ratio=0, call_volume_trigger=False,
            put_volume=0, put_volume_baseline=0, put_volume_ratio=0, put_volume_trigger=False,
            short_term_call_volume=0, short_term_call_baseline=0, short_term_call_ratio=0, short_term_call_trigger=False,
            otm_call_volume=0, otm_call_baseline=0, otm_call_ratio=0, otm_call_trigger=False,
            call_oi_delta=0, call_oi_baseline=0, call_oi_ratio=0, call_oi_trigger=False,
            unusual_activity_score=0.0, insider_probability=0.0, notes="No options data available"
        )

# Global anomaly detector instance
anomaly_detector = AnomalyDetector() 