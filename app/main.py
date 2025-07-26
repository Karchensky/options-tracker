import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import numpy as np
from sqlalchemy import create_engine, text
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Options Tracker Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for sleek monitoring theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Borda:wght@300;400;500;600;700&display=swap');
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Borda', sans-serif;
    }
    
    .stApp {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
    }
    
    .stSidebar {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .anomaly-high {
        background: rgba(255, 0, 0, 0.1);
        border-left: 4px solid #ff0000;
    }
    
    .anomaly-medium {
        background: rgba(255, 165, 0, 0.1);
        border-left: 4px solid #ffa500;
    }
    
    .anomaly-low {
        background: rgba(255, 255, 0, 0.1);
        border-left: 4px solid #ffff00;
    }
    
    h1, h2, h3 {
        font-family: 'Borda', sans-serif;
        font-weight: 600;
        color: #2c3e50;
    }
    
    .stSelectbox, .stSlider, .stRadio {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_database_connection():
    """Get database connection with caching."""
    try:
        engine = create_engine(config.SUPABASE_DB_URL)
        return engine
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Data loading functions
@st.cache_data(ttl=3600)
def load_snapshot_dates():
    """Load available snapshot dates."""
    engine = get_database_connection()
    if not engine:
        return []
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT snapshot_date 
                FROM option_anomalies 
                ORDER BY snapshot_date DESC
            """))
            return [row[0] for row in result]
    except Exception as e:
        st.error(f"Error loading dates: {e}")
        return []

@st.cache_data(ttl=3600)
def load_symbols():
    """Load available symbols."""
    engine = get_database_connection()
    if not engine:
        return []
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT s.symbol 
                FROM stocks s
                JOIN option_anomalies oa ON s.id = oa.stock_id
                ORDER BY s.symbol
            """))
            return [row[0] for row in result]
    except Exception as e:
        st.error(f"Error loading symbols: {e}")
        return []

@st.cache_data(ttl=1800)
def load_anomalies(snapshot_date):
    """Load anomalies for a specific date."""
    engine = get_database_connection()
    if not engine:
        return pd.DataFrame()
    
    try:
        query = text("""
            SELECT 
                s.symbol,
                oa.call_volume_ratio,
                oa.put_volume_ratio,
                oa.short_term_call_ratio,
                oa.otm_call_ratio,
                oa.call_oi_ratio,
                oa.unusual_activity_score,
                oa.insider_probability,
                oa.notes,
                oa.call_volume_trigger,
                oa.put_volume_trigger,
                oa.short_term_call_trigger,
                oa.otm_call_trigger,
                oa.call_oi_trigger
            FROM option_anomalies oa
            JOIN stocks s ON oa.stock_id = s.id
            WHERE oa.snapshot_date = :date
            AND (oa.call_volume_trigger = true OR oa.put_volume_trigger = true 
                 OR oa.short_term_call_trigger = true OR oa.otm_call_trigger = true 
                 OR oa.call_oi_trigger = true)
            ORDER BY oa.insider_probability DESC
        """)
        
        return pd.read_sql(query, engine, params={"date": snapshot_date})
    except Exception as e:
        st.error(f"Error loading anomalies: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_option_data(snapshot_date, symbol):
    """Load options data for a specific symbol and date."""
    engine = get_database_connection()
    if not engine:
        return pd.DataFrame()
    
    try:
        query = text("""
            SELECT 
                od.expiration,
                od.strike,
                od.option_type,
                od.volume,
                od.open_interest,
                od.implied_volatility,
                od.delta,
                od.gamma,
                od.theta,
                od.vega
            FROM option_data od
            JOIN stocks s ON od.stock_id = s.id
            WHERE od.snapshot_date = :date AND s.symbol = :symbol
        """)
        
        return pd.read_sql(query, engine, params={"date": snapshot_date, "symbol": symbol})
    except Exception as e:
        st.error(f"Error loading option data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_stock_price(snapshot_date, symbol):
    """Load stock price for a specific symbol and date."""
    engine = get_database_connection()
    if not engine:
        return None
    
    try:
        query = text("""
            SELECT close_price, open_price, high_price, low_price, volume
            FROM stock_price_snapshots sps
            JOIN stocks s ON sps.stock_id = s.id
            WHERE sps.snapshot_date = :date AND s.symbol = :symbol
        """)
        
        result = engine.execute(query, {"date": snapshot_date, "symbol": symbol})
        row = result.fetchone()
        return row if row else None
    except Exception as e:
        st.error(f"Error loading stock price: {e}")
        return None

# Main app
def main():
    st.title("Options Tracker Dashboard")
    st.markdown("---")
    
    # Sidebar filters
    st.sidebar.title("Filters")
    
    # Date selection
    snapshot_dates = load_snapshot_dates()
    if not snapshot_dates:
        st.error("No data available. Please run the data collection first.")
        return
    
    selected_date = st.sidebar.selectbox(
        "Snapshot Date",
        snapshot_dates,
        index=0
    )
    
    # Symbol selection
    symbols = load_symbols()
    selected_symbol = st.sidebar.selectbox(
        "Select Ticker",
        symbols,
        index=0 if symbols else None
    )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Anomaly Overview")
        display_anomaly_overview(selected_date)
    
    with col2:
        st.subheader("Quick Stats")
        display_quick_stats(selected_date)
    
    # Detailed analysis
    if selected_symbol:
        st.subheader(f"Detailed Analysis: {selected_symbol}")
        display_detailed_analysis(selected_date, selected_symbol)

def display_anomaly_overview(snapshot_date):
    """Display anomaly overview for the selected date."""
    anomalies_df = load_anomalies(snapshot_date)
    
    if anomalies_df.empty:
        st.info("No anomalies detected for this date.")
        return
    
    # Create anomaly cards
    for _, row in anomalies_df.iterrows():
        # Determine risk level
        if row['insider_probability'] >= 0.7:
            risk_class = "anomaly-high"
            risk_emoji = "🔴"
        elif row['insider_probability'] >= 0.4:
            risk_class = "anomaly-medium"
            risk_emoji = "🟡"
        else:
            risk_class = "anomaly-low"
            risk_emoji = "🟢"
        
        with st.container():
            st.markdown(f"""
            <div class="metric-card {risk_class}">
                <h4>{risk_emoji} {row['symbol']} - {row['insider_probability']:.1%} Insider Probability</h4>
                <p><strong>Activity Score:</strong> {row['unusual_activity_score']:.2f}</p>
                <p><strong>Notes:</strong> {row['notes']}</p>
            </div>
            """, unsafe_allow_html=True)

def display_quick_stats(snapshot_date):
    """Display quick statistics."""
    anomalies_df = load_anomalies(snapshot_date)
    
    if anomalies_df.empty:
        st.info("No data available")
        return
    
    # Calculate stats
    total_anomalies = len(anomalies_df)
    high_risk = len(anomalies_df[anomalies_df['insider_probability'] >= 0.7])
    medium_risk = len(anomalies_df[(anomalies_df['insider_probability'] >= 0.4) & (anomalies_df['insider_probability'] < 0.7)])
    low_risk = len(anomalies_df[anomalies_df['insider_probability'] < 0.4])
    
    avg_probability = anomalies_df['insider_probability'].mean()
    
    # Display metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Anomalies", total_anomalies)
        st.metric("High Risk", high_risk, delta=f"{high_risk/total_anomalies:.1%}" if total_anomalies > 0 else "0%")
    
    with col2:
        st.metric("Avg Probability", f"{avg_probability:.1%}")
        st.metric("Medium Risk", medium_risk, delta=f"{medium_risk/total_anomalies:.1%}" if total_anomalies > 0 else "0%")
    
    # Risk distribution chart
    risk_data = pd.DataFrame({
        'Risk Level': ['High', 'Medium', 'Low'],
        'Count': [high_risk, medium_risk, low_risk],
        'Color': ['#ff0000', '#ffa500', '#ffff00']
    })
    
    chart = alt.Chart(risk_data).mark_bar().encode(
        x='Risk Level',
        y='Count',
        color=alt.Color('Color', scale=None)
    ).properties(height=200)
    
    st.altair_chart(chart, use_container_width=True)

def display_detailed_analysis(snapshot_date, symbol):
    """Display detailed analysis for a specific symbol."""
    option_data = load_option_data(snapshot_date, symbol)
    stock_price = load_stock_price(snapshot_date, symbol)
    
    if option_data.empty:
        st.warning(f"No options data available for {symbol} on {snapshot_date}")
        return
    
    # Stock price info
    if stock_price:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Close Price", f"${stock_price[0]:.2f}")
        with col2:
            st.metric("Volume", f"{stock_price[4]:,}")
        with col3:
            st.metric("High", f"${stock_price[2]:.2f}")
        with col4:
            st.metric("Low", f"${stock_price[3]:.2f}")
    
    # Options analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Volume Analysis", "Open Interest", "Greeks", "Timeline"])
    
    with tab1:
        display_volume_analysis(option_data, symbol)
    
    with tab2:
        display_open_interest_analysis(option_data, symbol)
    
    with tab3:
        display_greeks_analysis(option_data, symbol)
    
    with tab4:
        display_timeline_analysis(symbol)

def display_volume_analysis(option_data, symbol):
    """Display volume analysis."""
    # Volume by option type
    volume_by_type = option_data.groupby('option_type')['volume'].sum().reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Volume by Option Type")
        chart = alt.Chart(volume_by_type).mark_bar().encode(
            x='option_type',
            y='volume',
            color='option_type'
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.subheader("Volume Distribution")
        # Volume heatmap by strike and expiration
        if not option_data.empty:
            heatmap_data = option_data.pivot_table(
                values='volume', 
                index='strike', 
                columns='expiration', 
                aggfunc='sum'
            ).fillna(0)
            
            fig = px.imshow(
                heatmap_data,
                title=f"Volume Heatmap - {symbol}",
                labels=dict(x="Expiration", y="Strike", color="Volume"),
                aspect="auto"
            )
            st.plotly_chart(fig, use_container_width=True)

def display_open_interest_analysis(option_data, symbol):
    """Display open interest analysis."""
    # OI by option type
    oi_by_type = option_data.groupby('option_type')['open_interest'].sum().reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Open Interest by Option Type")
        chart = alt.Chart(oi_by_type).mark_bar().encode(
            x='option_type',
            y='open_interest',
            color='option_type'
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.subheader("OI vs Volume Ratio")
        option_data['oi_volume_ratio'] = option_data['open_interest'] / option_data['volume'].replace(0, 1)
        
        chart = alt.Chart(option_data).mark_circle().encode(
            x='strike',
            y='oi_volume_ratio',
            color='option_type',
            size='volume'
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

def display_greeks_analysis(option_data, symbol):
    """Display Greeks analysis."""
    # Filter for options with Greeks data
    greeks_data = option_data.dropna(subset=['delta', 'gamma', 'theta', 'vega'])
    
    if greeks_data.empty:
        st.info("No Greeks data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Delta Distribution")
        chart = alt.Chart(greeks_data).mark_histogram().encode(
            x='delta',
            color='option_type'
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.subheader("Gamma Distribution")
        chart = alt.Chart(greeks_data).mark_histogram().encode(
            x='gamma',
            color='option_type'
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)
    
    # Greeks correlation
    st.subheader("Greeks Correlation Matrix")
    greeks_corr = greeks_data[['delta', 'gamma', 'theta', 'vega']].corr()
    
    fig = px.imshow(
        greeks_corr,
        title="Greeks Correlation Matrix",
        color_continuous_scale='RdBu',
        aspect="auto"
    )
    st.plotly_chart(fig, use_container_width=True)

def display_timeline_analysis(symbol):
    """Display timeline analysis."""
    st.subheader("Historical Anomaly Timeline")
    
    # Load historical anomalies for this symbol
    engine = get_database_connection()
    if not engine:
        st.error("Database connection failed")
        return
    
    try:
        query = text("""
            SELECT 
                oa.snapshot_date,
                oa.insider_probability,
                oa.unusual_activity_score,
                oa.call_volume_ratio,
                oa.put_volume_ratio
            FROM option_anomalies oa
            JOIN stocks s ON oa.stock_id = s.id
            WHERE s.symbol = :symbol
            ORDER BY oa.snapshot_date DESC
            LIMIT 30
        """)
        
        timeline_data = pd.read_sql(query, engine, params={"symbol": symbol})
        
        if timeline_data.empty:
            st.info("No historical data available")
            return
        
        # Create timeline chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timeline_data['snapshot_date'],
            y=timeline_data['insider_probability'],
            mode='lines+markers',
            name='Insider Probability',
            line=dict(color='red', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=timeline_data['snapshot_date'],
            y=timeline_data['unusual_activity_score'],
            mode='lines+markers',
            name='Activity Score',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title=f"Anomaly Timeline - {symbol}",
            xaxis_title="Date",
            yaxis_title="Insider Probability",
            yaxis2=dict(title="Activity Score", overlaying="y", side="right"),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading timeline data: {e}")

if __name__ == "__main__":
    main() 