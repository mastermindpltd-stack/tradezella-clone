import streamlit as st
import pandas as pd
import plotly.express as px

from auth import get_authenticator
from database import create_table, get_connection

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Trade Journal",
    layout="wide"
)

# -------------------------------------------------
# GLOBAL PREMIUM THEME (TradeZella-style)
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
    box-shadow: 0 10px 30px rgba(0,0,0,0.45);
}

.card-title {
    color: #8b949e;
    font-size: 13px;
}

.card-value {
    color: #58a6ff;
    font-size: 30px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
authenticator = get_authenticator()
name, auth_status, username = authenticator.login("Login", "main")

if auth_status is False:
    st.error("Invalid credentials")
    st.stop()

if auth_status is None:
    st.stop()

authenticator.logout("Logout", "sidebar")

# -------------------------------------------------
# SIDEBAR NAV
# -------------------------------------------------
st.sidebar.markdown("## 📥 Import Trades (CSV)")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV",
    type=["csv"]
)
if uploaded_file is not None:
    csv_df = pd.read_csv(uploaded_file)

    st.subheader("📄 CSV Preview")
    st.dataframe(csv_df.head(), use_container_width=True)

    required_cols = {"pair","direction","entry","stoploss","takeprofit","lot"}

    if not required_cols.issubset(csv_df.columns):
        st.error(f"CSV must contain columns: {required_cols}")
    else:
        st.success("CSV format looks good ✅")

st.sidebar.markdown("## 📘 Trade Journal")
st.sidebar.caption("TradeZella-style analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Trades", "Analytics"]
)

# -------------------------------------------------
# DB INIT
# -------------------------------------------------
create_table()

# -------------------------------------------------
# LOAD USER DATA
# -------------------------------------------------
conn = get_connection()
df = pd.read_sql(
    "SELECT * FROM trades WHERE username = ?",
    conn,
    params=(username,)
)
conn.close()

# -------------------------------------------------
# ADD TRADE (TOP ACTION – like TradeZella)
# -------------------------------------------------
with st.expander("➕ Add Trade", expanded=False):
    with st.form("trade_form"):
        pair = st.selectbox("Pair", ["EURUSD","GBPUSD","USDJPY","XAUUSD","BTCUSD"])
        direction = st.radio("Direction", ["Buy","Sell"], horizontal=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            entry = st.number_input("Entry", format="%.5f")
            stoploss = st.number_input("Stop Loss", format="%.5f")
        with c2:
            takeprofit = st.number_input("Take Profit", format="%.5f")
            lot = st.number_input("Lot Size", min_value=0.01, step=0.01)
        with c3:
            session = st.selectbox("Session", ["London","NY","Asia"])
            result = st.selectbox("Result", ["Win","Loss"])

        submit = st.form_submit_button("Save Trade")

    if submit:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO trades
            (username,pair,direction,entry,stoploss,takeprofit,lot)
            VALUES (?,?,?,?,?,?,?)
            """,
            (username,pair,direction,entry,stoploss,takeprofit,lot)
        )
        conn.commit()
        conn.close()
        st.success("Trade added")

# -------------------------------------------------
# STOP IF NO DATA
# -------------------------------------------------
if df.empty:
    st.info("No trades yet")
    st.stop()

# -------------------------------------------------
# CALCULATIONS (TradeZella-style)
# -------------------------------------------------
df["PnL"] = df.apply(
    lambda x:
    (x["takeprofit"]-x["entry"])*x["lot"]
    if x["direction"]=="Buy"
    else (x["entry"]-x["takeprofit"])*x["lot"],
    axis=1
)

df["Risk"] = abs(df["entry"] - df["stoploss"]) * df["lot"]
df["Reward"] = abs(df["takeprofit"] - df["entry"]) * df["lot"]
df["RR"] = (df["Reward"] / df["Risk"]).round(2)
df["Equity"] = df["PnL"].cumsum()
df["Peak"] = df["Equity"].cummax()
df["Drawdown"] = df["Equity"] - df["Peak"]

# -------------------------------------------------
# METRICS
# -------------------------------------------------
total = len(df)
winrate = round((df["PnL"]>0).mean()*100,2)
avg_rr = round(df["RR"].mean(),2)
net_pnl = round(df["PnL"].sum(),2)
max_dd = round(df["Drawdown"].min(),2)

def metric(title,value):
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
    st.markdown("## Dashboard")

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: metric("Trades", total)
    with c2: metric("Win Rate", f"{winrate}%")
    with c3: metric("Avg RR", avg_rr)
    with c4: metric("Max DD", max_dd)
    with c5: metric("Net PnL", net_pnl)

    st.markdown("### Equity Curve")

    fig = px.line(df, y="Equity")
    fig.update_traces(line=dict(width=3,color="#58a6ff"))
    fig.update_layout(
        height=420,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9",
        xaxis=dict(showgrid=False,showticklabels=False),
        yaxis=dict(gridcolor="#21262d")
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------
# TRADES
# -------------------------------------------------
elif page == "Trades":
    st.markdown("## Trades")
    st.dataframe(
        df.style
        .applymap(lambda v: "color:#00ff9c" if isinstance(v,(int,float)) and v>0 else "color:#ff5c5c", subset=["PnL"])
        .format({"PnL":"{:.2f}","RR":"{:.2f}"}),
        use_container_width=True
    )

# -------------------------------------------------
# ANALYTICS
# -------------------------------------------------
elif page == "Analytics":
    st.markdown("## Analytics")

    st.markdown("### Drawdown")
    dd = px.area(df, y="Drawdown")
    dd.update_layout(
        height=300,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9"
    )
    st.plotly_chart(dd, use_container_width=True)

    st.markdown("### Pair Performance")
    pair_stats = (
        df.groupby("pair")
        .agg(
            Trades=("PnL","count"),
            WinRate=("PnL",lambda x: round((x>0).mean()*100,2)),
            NetPnL=("PnL","sum"),
            AvgRR=("RR","mean")
        )
        .reset_index()
    )
    st.dataframe(pair_stats, use_container_width=True)


