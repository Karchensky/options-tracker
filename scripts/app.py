import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text
from config import SUPABASE_DB_URL
import numpy as np

st.set_page_config(page_title="Options Tracker", layout="wide")
engine = create_engine(SUPABASE_DB_URL)

# ========== CACHING FUNCTIONS ==========
# Snapshot date list
@st.cache_data(ttl=3600)
def load_snapshot_dates():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT snapshot_date FROM option_anomalies ORDER BY snapshot_date DESC"))
        return [row[0] for row in result]

# Symbol list
@st.cache_data(ttl=3600)
def load_symbols():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT symbol FROM option_anomalies ORDER BY symbol"))
        return [row[0] for row in result]

# Option data for a specific snapshot date and symbol
def load_option_data(snapshot_date, symbol):
    with engine.connect() as conn:
        query = text("""
            SELECT symbol, expiration, strike, side, volume, open_interest
            FROM option_data
            WHERE snapshot_date = :date AND symbol = :symbol
        """)
        return pd.read_sql(query, conn, params={"date": snapshot_date, "symbol": symbol})

# Close price for a specific snapshot date and symbol
@st.cache_data(ttl=3600)
def load_stock_prices(snapshot_date, symbol):
    with engine.connect() as conn:
        query = text("""
            SELECT close_price
            FROM stock_price_snapshot
            WHERE snapshot_date = :date AND symbol = :symbol
        """)
        return pd.read_sql(query, conn, params={"date": snapshot_date, "symbol": symbol})

# Load anomalies for a specific snapshot date
def load_anomalies(snapshot_date):
    with engine.connect() as conn:
        query = text("""
            SELECT symbol, ov_call_ratio, ov_put_ratio, short_call_ratio, otm_call_ratio, oi_call_ratio
            FROM option_anomalies
            WHERE snapshot_date = :date
              AND (ov_trigger_ind = 1 OR ov_put_trigger_ind = 1 OR short_call_trigger_ind = 1
                   OR otm_call_trigger_ind = 1 OR oi_call_trigger_ind = 1)
        """)
        return pd.read_sql(query, conn, params={"date": snapshot_date})

# ========== SIDEBAR ==========

# These are primary filters that will be used to filter the main data
st.sidebar.title("Primary Filters")
snapshot_dates = load_snapshot_dates()
available_symbols = load_symbols()

selected_date = st.sidebar.selectbox("Snapshot Date", snapshot_dates)
selected_symbol = st.sidebar.selectbox("Select Ticker", available_symbols)

st.sidebar.title("Option Filters")

# Once a symbol & date are selected, we can load the option data
# Load option data for selected snapshot date and symbol
option_data = load_option_data(selected_date, selected_symbol)

# Dynamically filter expiration and strike ranges based on current filtered data
expirations = pd.to_datetime(option_data["expiration"].unique())
if len(expirations) == 0:
    min_exp, max_exp = pd.Timestamp("2000-01-01"), pd.Timestamp("2000-01-01")
else:
    min_exp, max_exp = expirations.min(), expirations.max()

# Convert to datetime.date for Streamlit slider
min_exp_date = min_exp.date()
max_exp_date = max_exp.date()

selected_exp_range = st.sidebar.slider(
    "Expiration Date Range", min_exp_date, max_exp_date, (min_exp_date, max_exp_date), format="YYYY-MM-DD"
)

strikes = option_data["strike"].unique()
if len(strikes) == 0:
    min_strike, max_strike = 0.0, 0.0
else:
    min_strike, max_strike = float(strikes.min()), float(strikes.max())
selected_strike_range = st.sidebar.slider(
    "Strike Price Range", min_strike, max_strike, (min_strike, max_strike)
)

# Swap between volume and open interest
metric_type = st.sidebar.radio("View:", ["volume", "open_interest"], horizontal=True)

# Filter data for main display based on all slicers
filtered_data = option_data[
    (pd.to_datetime(option_data["expiration"]) >= pd.Timestamp(selected_exp_range[0])) &
    (pd.to_datetime(option_data["expiration"]) <= pd.Timestamp(selected_exp_range[1])) &
    (option_data["strike"] >= selected_strike_range[0]) &
    (option_data["strike"] <= selected_strike_range[1])
]

calls = filtered_data[filtered_data["side"] == "CALL"].copy()
puts = filtered_data[filtered_data["side"] == "PUT"].copy()

st.title(f"Options Tracker")

# ========== ANOMALY TABLE ==========
anomalies_df = load_anomalies(selected_date)
if anomalies_df.empty:
    st.info("No anomalies detected for the selected snapshot date.")
else:
    st.dataframe(anomalies_df, use_container_width=True)

st.markdown("---")

# ========== EXPIRATION + STRIKE POPULATION CHARTS ==========
col1, col2 = st.columns(2)

with col1:
    st.subheader("Expiration Date")
    exp_chart = alt.Chart(filtered_data).transform_calculate(
        dir="datum.side === 'CALL' ? 1 : -1",
        adjusted_metric=f"datum.{metric_type} * (datum.side === 'CALL' ? 1 : -1)"
    ).mark_bar(opacity=0.7).encode(
        x=alt.X("adjusted_metric:Q", title=f"{metric_type.title()}"),
        y=alt.Y("expiration:T", sort=alt.SortField(field="expiration", order="descending"), title="Expiration"),
        color=alt.Color(scale=alt.Scale(domain=["CALL", "PUT"], range=["steelblue", "orange"]))
    ).properties(height=350)

    st.altair_chart(exp_chart, use_container_width=True)

with col2:
    st.subheader("Strike Price")
    strike_chart = alt.Chart(filtered_data).transform_calculate(
        dir="datum.side === 'CALL' ? 1 : -1",
        adjusted_metric=f"datum.{metric_type} * (datum.side === 'CALL' ? 1 : -1)"
    ).mark_bar(opacity=0.7).encode(
        x=alt.X("adjusted_metric:Q", title=f"{metric_type.title()}"),
        y=alt.Y("strike:Q", bin=alt.Bin(maxbins=40), title="Strike"),
        color=alt.Color(scale=alt.Scale(domain=["CALL", "PUT"], range=["steelblue", "orange"]))
    ).properties(height=350)

    # Add horizontal line at close price
    stock_prices_df = load_stock_prices(selected_date, selected_symbol)
    close_price = stock_prices_df["close_price"].values
    if len(close_price) > 0:
        rule = alt.Chart(pd.DataFrame({"strike": [close_price[0]]})).mark_rule(color="red", strokeDash=[4,4]).encode(
            y="strike:Q"
        )
        strike_chart = strike_chart + rule

    st.altair_chart(strike_chart, use_container_width=True)

# ========== HEATMAPS ==========
col3, col4 = st.columns(2)

def plot_heatmap(df):
    df = df.copy()
    df["expiration"] = pd.to_datetime(df["expiration"])
    df["expiration_str"] = df["expiration"].dt.strftime("%Y-%m-%d")  # to treat as labels

    # Handle color scaling (robust)
    vmin, vmax = df[metric_type].quantile([0.01, 0.99]).tolist()
    if vmax <= vmin:
        vmax = df[metric_type].max()
        vmin = 0

    base = alt.Chart(df).mark_rect().encode(
        x=alt.X("expiration_str:N", title="Expiration", sort="ascending"),
        y=alt.Y("strike:Q", title="Strike Price", bin=alt.Bin(maxbins=60), sort="ascending"),
        color=alt.Color(f"{metric_type}:Q", scale=alt.Scale(scheme="greenblue", domain=[vmin, vmax])),
        tooltip=["expiration_str", "strike", f"{metric_type}:Q"]
    ).properties(height=400)

    if close_price is not None:
        line = alt.Chart(pd.DataFrame({"strike": [close_price[0]]})).mark_rule(
            color="red", strokeDash=[4, 4]
        ).encode(y="strike:Q")
        base += line

    return base

with col3:
    st.subheader("CALL Heatmap")
    st.altair_chart(plot_heatmap(calls), use_container_width=True)

with col4:
    st.subheader("PUT Heatmap")
    st.altair_chart(plot_heatmap(puts), use_container_width=True)

# Divider
st.markdown("---")

# ========== HISTORICAL RATIO CHART ==========
st.subheader("Historical Ratios Over Time")

with engine.connect() as conn:
    hist_data = pd.read_sql(text("""
        SELECT snapshot_date, expiration, strike, side, volume, open_interest
        FROM option_data
        WHERE symbol = :symbol
        ORDER BY snapshot_date
    """), conn, params={"symbol": selected_symbol})

# Filter by user-selected expiration and strike
filtered_hist = hist_data[
    (hist_data["expiration"] >= selected_exp_range[0]) &
    (hist_data["expiration"] <= selected_exp_range[1]) &
    (hist_data["strike"] >= selected_strike_range[0]) &
    (hist_data["strike"] <= selected_strike_range[1])
].copy()

# Get close prices for OTM calculation
close_prices_df = load_stock_prices(hist_data["snapshot_date"].max(), selected_symbol)
close_price = close_prices_df["close_price"].values[0] if not close_prices_df.empty else None

# Helper to get rolling average for a side and filter
def get_rolling_avg(df, side, filter_func=None):
    df_side = df[df["side"] == side]
    if filter_func is not None:
        df_side = df_side[filter_func(df_side)]
    grouped = df_side.groupby("snapshot_date")["volume"].sum()
    rolling_avg = grouped.rolling(window=14, min_periods=3).mean()
    return rolling_avg

# Helper to get today's volume for a side and filter
def get_today_volume(df, side, date, filter_func=None):
    df_side = df[(df["side"] == side) & (df["snapshot_date"] == date)]
    if filter_func is not None:
        df_side = df_side[filter_func(df_side)]
    return df_side["volume"].sum()

# Helper for OI ratio
def get_oi_ratio(df, date):
    today_oi = df[(df["side"] == "CALL") & (df["snapshot_date"] == date)]["open_interest"].sum()
    yesterday = pd.to_datetime(date) - pd.Timedelta(days=1)
    yest_oi = df[(df["side"] == "CALL") & (df["snapshot_date"] == str(yesterday))]["open_interest"].sum()
    oi_base = yest_oi if yest_oi > 0 else 1
    return today_oi / oi_base if oi_base > 1 else 1

# Prepare time series for each ratio
ratios = []
dates = sorted(filtered_hist["snapshot_date"].unique())
for date in dates:
    # OV Call
    call_rolling = get_rolling_avg(filtered_hist, "CALL")
    call_base = call_rolling.loc[:date].iloc[-2] if len(call_rolling.loc[:date]) > 1 else np.nan
    call_today = get_today_volume(filtered_hist, "CALL", date)
    ov_call_ratio = call_today / call_base if call_base and call_base > 0 else np.nan

    # OV Put
    put_rolling = get_rolling_avg(filtered_hist, "PUT")
    put_base = put_rolling.loc[:date].iloc[-2] if len(put_rolling.loc[:date]) > 1 else np.nan
    put_today = get_today_volume(filtered_hist, "PUT", date)
    ov_put_ratio = put_today / put_base if put_base and put_base > 0 else np.nan

    # Short Call (expiration <= date+7)
    short_filter = lambda df: pd.to_datetime(df["expiration"]) <= pd.to_datetime(date) + pd.Timedelta(days=7)
    short_call_rolling = get_rolling_avg(filtered_hist, "CALL", short_filter)
    short_call_base = short_call_rolling.loc[:date].iloc[-2] if len(short_call_rolling.loc[:date]) > 1 else np.nan
    short_call_today = get_today_volume(filtered_hist, "CALL", date, short_filter)
    short_call_ratio = short_call_today / short_call_base if short_call_base and short_call_base > 0 else np.nan

    # OTM Call (strike > close_price * 1.1)
    if close_price is not None:
        otm_filter = lambda df: df["strike"] > close_price * 1.1
        otm_call_rolling = get_rolling_avg(filtered_hist, "CALL", otm_filter)
        otm_call_base = otm_call_rolling.loc[:date].iloc[-2] if len(otm_call_rolling.loc[:date]) > 1 else np.nan
        otm_call_today = get_today_volume(filtered_hist, "CALL", date, otm_filter)
        otm_call_ratio = otm_call_today / otm_call_base if otm_call_base and otm_call_base > 0 else np.nan
    else:
        otm_call_ratio = np.nan

    # OI Ratio
    oi_ratio = get_oi_ratio(filtered_hist, date)

    ratios.append({
        "snapshot_date": date,
        "ov_call_ratio": ov_call_ratio,
        "ov_put_ratio": ov_put_ratio,
        "short_call_ratio": short_call_ratio,
        "otm_call_ratio": otm_call_ratio,
        "oi_call_ratio": oi_ratio
    })

ratios_df = pd.DataFrame(ratios)

# Melt for Altair
ratios_long = ratios_df.melt(id_vars="snapshot_date", 
                             value_vars=["ov_call_ratio", "ov_put_ratio", "short_call_ratio", "otm_call_ratio", "oi_call_ratio"],
                             var_name="ratio_type", value_name="ratio")

# Plot
if not ratios_long.dropna(subset=["ratio"]).empty:
    selected_ratios = st.multiselect(
        "Select Ratios to Show",
        ["ov_call_ratio", "ov_put_ratio", "short_call_ratio", "otm_call_ratio", "oi_call_ratio"],
        default=["ov_call_ratio", "ov_put_ratio", "short_call_ratio", "otm_call_ratio", "oi_call_ratio"]
    )
    plot_df = ratios_long[ratios_long["ratio_type"].isin(selected_ratios)]

    ratio_chart = alt.Chart(plot_df).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Snapshot Date"),
        y=alt.Y("ratio:Q", title="Anomaly Ratio"),
        color=alt.Color("ratio_type:N", title="Ratio Type"),
        tooltip=["snapshot_date", "ratio_type", "ratio"]
    ).properties(height=400)

    st.altair_chart(ratio_chart, use_container_width=True)
else:
    st.info("No data available to compute historical anomaly ratios.")