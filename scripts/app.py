import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text
from config import SUPABASE_DB_URL
import numpy as np

st.set_page_config(page_title="Options Tracker", layout="wide")
engine = create_engine(SUPABASE_DB_URL)

# ========== CACHING FUNCTIONS ==========
@st.cache_data(ttl=3600)
def load_snapshot_dates():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT snapshot_date FROM option_data ORDER BY snapshot_date DESC"))
        return [row[0] for row in result]

@st.cache_data(ttl=3600)
def load_option_data(snapshot_date):
    with engine.connect() as conn:
        query = text("""
            SELECT symbol, expiration, strike, side, volume, open_interest
            FROM option_data
            WHERE snapshot_date = :date
        """)
        return pd.read_sql(query, conn, params={"date": snapshot_date})

@st.cache_data(ttl=3600)
def load_stock_prices(snapshot_date):
    with engine.connect() as conn:
        query = text("""
            SELECT symbol, close_price
            FROM stock_price_snapshot
            WHERE snapshot_date = :date
        """)
        return pd.read_sql(query, conn, params={"date": snapshot_date})

@st.cache_data(ttl=3600)
def load_anomalies(snapshot_date):
    with engine.connect() as conn:
        query = text("""
            SELECT symbol, ov_call_ratio, ov_put_ratio, short_call_ratio,
                   otm_call_ratio, oi_call_ratio
            FROM option_anomalies
            WHERE snapshot_date = :date
              AND (ov_trigger_ind = 1 OR ov_put_trigger_ind = 1 OR short_call_trigger_ind = 1
                   OR otm_call_trigger_ind = 1 OR oi_call_trigger_ind = 1)
        """)
        return pd.read_sql(query, conn, params={"date": snapshot_date})

# ========== SIDEBAR ==========
st.sidebar.title("Options Tracker")
snapshot_dates = load_snapshot_dates()
selected_date = st.sidebar.selectbox("Snapshot Date", snapshot_dates)

option_data = load_option_data(selected_date)
stock_prices_df = load_stock_prices(selected_date)

available_symbols = sorted(option_data["symbol"].unique())
selected_symbol = st.sidebar.selectbox("Symbol for Ratio Time Series", available_symbols)
metric_type = st.sidebar.radio("Metric:", ["volume", "open_interest"], horizontal=True)

min_exp, max_exp = option_data["expiration"].min(), option_data["expiration"].max()
selected_exp_range = st.sidebar.slider("Expiration Date Range", min_exp, max_exp, (min_exp, max_exp))

min_strike, max_strike = float(option_data["strike"].min()), float(option_data["strike"].max())
selected_strike_range = st.sidebar.slider("Strike Price Range", min_strike, max_strike, (min_strike, max_strike))

# ========== FILTERED DATA ==========
filtered_data = option_data[
    (option_data["expiration"] >= selected_exp_range[0]) &
    (option_data["expiration"] <= selected_exp_range[1]) &
    (option_data["strike"] >= selected_strike_range[0]) &
    (option_data["strike"] <= selected_strike_range[1])
]

calls = filtered_data[filtered_data["side"] == "CALL"].copy()
puts = filtered_data[filtered_data["side"] == "PUT"].copy()

st.title(f"Options Dashboard")

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
    st.subheader("Expiration Breakdown")
    exp_chart = alt.Chart(filtered_data).transform_calculate(
        dir="datum.side === 'CALL' ? 1 : -1",
        adjusted_metric=f"datum.{metric_type} * (datum.side === 'CALL' ? 1 : -1)"
    ).mark_bar(opacity=0.7).encode(
        x=alt.X("adjusted_metric:Q", title=f"{metric_type.title()}"),
        y=alt.Y("expiration:T", sort=alt.SortField(field="expiration", order="descending"), title="Expiration"),
        color=alt.Color("side:N", scale=alt.Scale(domain=["CALL", "PUT"], range=["steelblue", "orange"]))
    ).properties(height=350)

    st.altair_chart(exp_chart, use_container_width=True)

with col2:
    st.subheader("Strike Breakdown")
    strike_chart = alt.Chart(filtered_data).transform_calculate(
        dir="datum.side === 'CALL' ? 1 : -1",
        adjusted_metric=f"datum.{metric_type} * (datum.side === 'CALL' ? 1 : -1)"
    ).mark_bar(opacity=0.7).encode(
        x=alt.X("adjusted_metric:Q", title=f"{metric_type.title()}"),
        y=alt.Y("strike:Q", bin=alt.Bin(maxbins=40), title="Strike"),
        color=alt.Color("side:N", scale=alt.Scale(domain=["CALL", "PUT"], range=["steelblue", "orange"]))
    ).properties(height=350)

    # Add horizontal line at close price
    close_price = stock_prices_df[stock_prices_df["symbol"] == selected_symbol]["close_price"].values
    if len(close_price) > 0:
        rule = alt.Chart(pd.DataFrame({"strike": [close_price[0]]})).mark_rule(color="red", strokeDash=[4,4]).encode(
            y="strike:Q"
        )
        strike_chart = strike_chart + rule

    st.altair_chart(strike_chart, use_container_width=True)

# ========== HEATMAPS ==========
col3, col4 = st.columns(2)

# Get close price if available
close_price = stock_prices_df.loc[
    stock_prices_df["symbol"] == selected_symbol, "close_price"
].values[0] if selected_symbol in stock_prices_df["symbol"].values else None

def plot_heatmap(df, title):
    df = df.copy()
    df["expiration"] = pd.to_datetime(df["expiration"])
    df["expiration_str"] = df["expiration"].dt.strftime("%Y-%m-%d")  # to treat as labels

    # Handle color scaling (robust)
    vmin, vmax = df[metric_type].quantile([0.05, 0.95]).tolist()
    if vmax <= vmin:
        vmax = df[metric_type].max()
        vmin = 0

    base = alt.Chart(df).mark_rect().encode(
        x=alt.X("expiration_str:N", title="Expiration", sort="ascending"),
        y=alt.Y("strike:Q", title="Strike Price", bin=alt.Bin(maxbins=60), sort="ascending"),
        color=alt.Color(f"{metric_type}:Q", scale=alt.Scale(scheme="greenblue", domain=[vmin, vmax])),
        tooltip=["expiration_str", "strike", f"{metric_type}:Q"]
    ).properties(height=400, title=title)

    if close_price is not None:
        line = alt.Chart(pd.DataFrame({"strike": [close_price]})).mark_rule(
            color="black", strokeDash=[4, 4]
        ).encode(y="strike:Q")
        base += line

    return base

with col3:
    st.subheader("CALL Heatmap")
    st.altair_chart(plot_heatmap(calls, "CALL Heatmap"), use_container_width=True)

with col4:
    st.subheader("PUT Heatmap")
    st.altair_chart(plot_heatmap(puts, "PUT Heatmap"), use_container_width=True)

# Divider
st.markdown("---")

# ========== HISTORICAL RATIO CHART ==========
st.subheader("Historical Ratios Over Time (Filtered)")

with engine.connect() as conn:
    hist_data = pd.read_sql(text("""
        SELECT snapshot_date, expiration, strike, side, volume, open_interest
        FROM option_data
        WHERE symbol = :symbol
        ORDER BY snapshot_date
    """), conn, params={"symbol": selected_symbol})

filtered_hist = hist_data[
    (hist_data["expiration"] >= selected_exp_range[0]) &
    (hist_data["expiration"] <= selected_exp_range[1]) &
    (hist_data["strike"] >= selected_strike_range[0]) &
    (hist_data["strike"] <= selected_strike_range[1])
]

def compute_ratios(df, side):
    df = df[df["side"] == side].copy()
    df = df.groupby("snapshot_date")[metric_type].sum().reset_index()
    df["rolling_avg"] = df[metric_type].rolling(window=14, min_periods=3).mean()
    df["ratio"] = df[metric_type] / df["rolling_avg"]
    df["side"] = side
    return df[["snapshot_date", "ratio", "side"]]

calls_ratio = compute_ratios(filtered_hist, "CALL")
puts_ratio = compute_ratios(filtered_hist, "PUT")
ratio_df = pd.concat([calls_ratio, puts_ratio])

if not ratio_df.empty:
    selected_sides = st.multiselect("Select Sides to Show", ["CALL", "PUT"], default=["CALL", "PUT"])
    filtered_ratio_df = ratio_df[ratio_df["side"].isin(selected_sides)]

    ratio_chart = alt.Chart(filtered_ratio_df).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Snapshot Date"),
        y=alt.Y("ratio:Q", title=f"{metric_type.title()} Ratio vs 14-day Avg"),
        color=alt.Color("side:N", scale=alt.Scale(domain=["CALL", "PUT"], range=["steelblue", "orange"])),
        tooltip=["snapshot_date", "side", "ratio"]
    ).properties(height=400)

    st.altair_chart(ratio_chart, use_container_width=True)
else:
    st.info("No data available to compute historical ratios.")