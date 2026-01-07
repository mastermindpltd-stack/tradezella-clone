import streamlit as st
import pandas as pd
import plotly.express as px

from database import create_table, get_connection
from auth import get_authenticator

# ---------------- THEME TOGGLE ----------------
theme = st.sidebar.radio("🎨 Theme", ["Dark", "Light"])

if theme == "Dark":
    st.markdown(
        """
        <style>
        body { background-color: #0e1117; color: #fafafa; }
        .stApp { background-color: #0e1117; }
        </style>
        """,
        unsafe_allow_html=True
    )


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Trade Journal",
    layout="wide"
)

# ---------------- LOGIN ----------------
authenticator = get_authenticator()
name, auth_status, username = authenticator.login("🔐 Login", "main")

if auth_status is False:
    st.error("❌ Wrong username or password")
    st.stop()

if auth_status is None:
    st.warning("Please login to continue")
    st.stop()

# ---------------- LOGOUT ----------------
authenticator.logout("🚪 Logout", "sidebar")
st.sidebar.success(f"Welcome {name}")
# ---------------- APP START ----------------
st.title("📘 Trade Journal Dashboard")

# Create DB table if not exists
create_table()

# ---------------- TRADE ENTRY FORM ----------------
with st.form("trade_form"):
    st.subheader("➕ Add New Trade")

    pair = st.selectbox(
        "Trading Pair",
        ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
    )

    direction = st.radio("Direction", ["Buy", "Sell"])

    col1, col2 = st.columns(2)

    with col1:
        entry = st.number_input("Entry Price", format="%.5f")
        stoploss = st.number_input("Stop Loss", format="%.5f")

    with col2:
        takeprofit = st.number_input("Take Profit", format="%.5f")
        lot = st.number_input("Lot Size", min_value=0.01, step=0.01)

    submit = st.form_submit_button("💾 Save Trade")

# ---------------- SAVE TRADE ----------------
if submit:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO trades (username, pair, direction, entry, stoploss, takeprofit, lot)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (username, pair, direction, entry, stoploss, takeprofit, lot)
    )
    conn.commit()
    conn.close()
    st.success("✅ Trade saved for your account")


# ---------------- LOAD TRADES ----------------
conn = get_connection()
df = pd.read_sql(
    "SELECT * FROM trades WHERE username = ?",
    conn,
    params=(username,)
)

conn.close()

if df.empty:
    st.info("No trades added yet")
    st.stop()

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.subheader("🔎 Filters")

selected_pair = st.sidebar.multiselect(
    "Select Pair",
    options=df["pair"].unique(),
    default=df["pair"].unique()
)

df = df[df["pair"].isin(selected_pair)]

# ---------------- CALCULATIONS ----------------
# ---------------- CALCULATIONS ----------------
def calculate_pnl(row):
    if row["direction"] == "Buy":
        return (row["takeprofit"] - row["entry"]) * row["lot"]
    else:
        return (row["entry"] - row["takeprofit"]) * row["lot"]

def calculate_risk(row):
    return abs(row["entry"] - row["stoploss"]) * row["lot"]

def calculate_reward(row):
    return abs(row["takeprofit"] - row["entry"]) * row["lot"]

df["PnL"] = df.apply(calculate_pnl, axis=1)
df["Risk"] = df.apply(calculate_risk, axis=1)
df["Reward"] = df.apply(calculate_reward, axis=1)

# RR (avoid divide by zero)
df["RR"] = df.apply(
    lambda x: round(x["Reward"] / x["Risk"], 2) if x["Risk"] != 0 else 0,
    axis=1
)

# Equity & Drawdown
df["Equity"] = df["PnL"].cumsum()
df["Peak"] = df["Equity"].cummax()
df["Drawdown"] = df["Equity"] - df["Peak"]

st.markdown("### 📊 Performance Overview")
st.markdown("---")

# ---------------- METRICS ----------------
st.subheader("📊 Advanced Performance Metrics")

total_trades = len(df)
wins = len(df[df["PnL"] > 0])
losses = len(df[df["PnL"] <= 0])
win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0
avg_rr = round(df["RR"].mean(), 2)
max_dd = round(df["Drawdown"].min(), 2)
net_pnl = round(df["PnL"].sum(), 2)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Total Trades", total_trades)
c2.metric("Win Rate %", win_rate)
c3.metric("Avg RR", avg_rr)
c4.metric("Max Drawdown", max_dd)
c5.metric("Net PnL", net_pnl)


# ---------------- EQUITY CURVE ----------------
st.subheader("📈 Equity Curve")

fig = px.line(df, y="Equity", title="Equity Curve")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📉 Drawdown Curve")
dd_fig = px.area(df, y="Drawdown", title="Drawdown Curve")
st.plotly_chart(dd_fig, use_container_width=True)

# ---------------- TRADE TABLE ----------------
st.subheader("📋 All Trades")
st.dataframe(df, use_container_width=True)

st.subheader("📌 Pair-wise Performance")

pair_stats = (
    df.groupby("pair")
    .agg(
        Trades=("PnL", "count"),
        WinRate=("PnL", lambda x: round((x[x > 0].count() / len(x)) * 100, 2)),
        NetPnL=("PnL", "sum"),
        AvgRR=("RR", "mean")
    )
    .reset_index()
)

st.dataframe(pair_stats, use_container_width=True)

