import streamlit as st
import pandas as pd
import plotly.express as px

from auth import get_authenticator
from database import create_table, get_connection

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="TradeZella Clone",
    layout="wide"
)

# -------------------------------------------------
# GLOBAL DARK THEME + PREMIUM UI
# -------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #0e1117;
}

.card {
    background: linear-gradient(145deg, #161b22, #0e1117);
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.45);
    text-align: left;
}

.card-title {
    color: #8b949e;
    font-size: 14px;
}

.card-value {
    color: #58a6ff;
    font-size: 28px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
authenticator = get_authenticator()
name, auth_status, username = authenticator.login("🔐 Login", "main")

if auth_status is False:
    st.error("❌ Wrong username or password")
    st.stop()

if auth_status is None:
    st.warning("Please login to continue")
    st.stop()

authenticator.logout("🚪 Logout", "sidebar")
st.sidebar.success(f"Welcome {name}")

# -------------------------------------------------
# SIDEBAR NAVIGATION
# -------------------------------------------------
st.sidebar.markdown("## 📘 TradeZella Clone")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Trades", "Analytics"]
)

# -------------------------------------------------
# DATABASE INIT
# -------------------------------------------------
create_table()

# -------------------------------------------------
# ADD TRADE FORM (COMMON)
# -------------------------------------------------
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
    st.success("✅ Trade saved")

# -------------------------------------------------
# LOAD USER TRADES
# -------------------------------------------------
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

# -------------------------------------------------
# CALCULATIONS
# -------------------------------------------------
def calculate_pnl(row):
    if row["direction"] == "Buy":
        return (row["takeprofit"] - row["entry"]) * row["lot"]
    else:
        return (row["entry"] - row["takeprofit"]) * row["lot"]

df["PnL"] = df.apply(calculate_pnl, axis=1)
df["Risk"] = abs(df["entry"] - df["stoploss"]) * df["lot"]
df["Reward"] = abs(df["takeprofit"] - df["entry"]) * df["lot"]
df["RR"] = df.apply(lambda x: round(x["Reward"] / x["Risk"], 2) if x["Risk"] != 0 else 0, axis=1)

df["Equity"] = df["PnL"].cumsum()
df["Peak"] = df["Equity"].cummax()
df["Drawdown"] = df["Equity"] - df["Peak"]

# -------------------------------------------------
# METRICS
# -------------------------------------------------
total_trades = len(df)
wins = len(df[df["PnL"] > 0])
win_rate = round((wins / total_trades) * 100, 2)
avg_rr = round(df["RR"].mean(), 2)
max_dd = round(df["Drawdown"].min(), 2)
net_pnl = round(df["PnL"].sum(), 2)

def card(title, value):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
if page == "Dashboard":
    st.markdown("## 📊 Performance Overview")
    st.markdown("---")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("Total Trades", total_trades)
    with c2: card("Win Rate", f"{win_rate}%")
    with c3: card("Avg RR", avg_rr)
    with c4: card("Max DD", max_dd)
    with c5: card("Net PnL", net_pnl)

    st.markdown("### 📈 Equity Curve")
    fig = px.line(df, y="Equity")
    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9"
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------
# TRADES PAGE
# -------------------------------------------------
elif page == "Trades":
    st.markdown("## 📋 All Trades")
    st.markdown("---")

    st.dataframe(
        df.style
        .applymap(
            lambda v: "color:#00ff9c" if isinstance(v,(int,float)) and v > 0 else "color:#ff5c5c",
            subset=["PnL"]
        )
        .format({"PnL":"{:.2f}", "RR":"{:.2f}"}),
        use_container_width=True
    )

# -------------------------------------------------
# ANALYTICS PAGE
# -------------------------------------------------
elif page == "Analytics":
    st.markdown("## 📉 Drawdown Analysis")
    st.markdown("---")

    dd_fig = px.area(df, y="Drawdown")
    dd_fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9"
    )
    st.plotly_chart(dd_fig, use_container_width=True)

    st.markdown("### 📌 Pair-wise Performance")
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
