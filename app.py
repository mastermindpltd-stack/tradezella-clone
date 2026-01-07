import streamlit as st
import pandas as pd
import plotly.express as px

from auth import get_authenticator
from database import create_table, get_connection

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Trade Journal", layout="wide")

# -------------------------------------------------
# GLOBAL DARK UI
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
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
}
.card-title {
    color: #8b949e;
    font-size: 13px;
}
.card-value {
    color: #58a6ff;
    font-size: 26px;
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
    st.error("Wrong username or password")
    st.stop()

if auth_status is None:
    st.stop()

authenticator.logout("Logout", "sidebar")
st.sidebar.success(f"Welcome {name}")

# -------------------------------------------------
# SIDEBAR NAV
# -------------------------------------------------
st.sidebar.markdown("## 📘 Trade Journal")
page = st.sidebar.radio("Navigate", ["Dashboard", "Trades", "Analytics"])

# -------------------------------------------------
# DATABASE INIT
# -------------------------------------------------
create_table()

# -------------------------------------------------
# CSV IMPORT WITH COLUMN MAPPING (SAFE)
# -------------------------------------------------
st.sidebar.markdown("### 📥 Import Trades (CSV)")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    csv_df = pd.read_csv(uploaded_file)

    st.subheader("📄 CSV Preview")
    st.dataframe(csv_df.head(), use_container_width=True)

    st.markdown("### 🧩 Map CSV Columns")

    pair_col = st.selectbox("Pair", csv_df.columns)
    direction_col = st.selectbox("Direction", csv_df.columns)
    entry_col = st.selectbox("Entry Price", csv_df.columns)
    stoploss_col = st.selectbox("Stop Loss", csv_df.columns)
    takeprofit_col = st.selectbox("Take Profit", csv_df.columns)
    lot_col = st.selectbox("Lot Size", csv_df.columns)

    if st.button("🚀 Import Trades"):
        conn = get_connection()
        imported = 0
        skipped = 0

        for _, row in csv_df.iterrows():
            try:
                conn.execute(
                    """
                    INSERT INTO trades
                    (username, pair, direction, entry, stoploss, takeprofit, lot)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        str(row[pair_col]),
                        str(row[direction_col]).capitalize(),
                        float(row[entry_col]),
                        float(row[stoploss_col]) if pd.notna(row[stoploss_col]) else 0,
                        float(row[takeprofit_col]) if pd.notna(row[takeprofit_col]) else 0,
                        float(row[lot_col])
                    )
                )
                imported += 1
            except Exception:
                skipped += 1

        conn.commit()
        conn.close()

        st.success(f"✅ Imported {imported} trades")
        if skipped > 0:
            st.warning(f"⚠️ Skipped {skipped} invalid rows")

        st.rerun()

# -------------------------------------------------
# ADD TRADE (MANUAL)
# -------------------------------------------------
with st.expander("➕ Add Trade"):
    with st.form("trade_form"):
        pair = st.selectbox("Pair", ["EURUSD","GBPUSD","USDJPY","XAUUSD","BTCUSD"])
        direction = st.radio("Direction", ["Buy","Sell"], horizontal=True)

        c1, c2 = st.columns(2)
        with c1:
            entry = st.number_input("Entry", format="%.5f")
            stoploss = st.number_input("Stop Loss", format="%.5f")
        with c2:
            takeprofit = st.number_input("Take Profit", format="%.5f")
            lot = st.number_input("Lot Size", min_value=0.01, step=0.01)

        submit = st.form_submit_button("Save Trade")

    if submit:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO trades
            (username, pair, direction, entry, stoploss, takeprofit, lot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, pair, direction, entry, stoploss, takeprofit, lot)
        )
        conn.commit()
        conn.close()
        st.success("Trade saved")
        st.experimental_rerun()

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
    st.info("No trades yet")
    st.stop()

# -------------------------------------------------
# CALCULATIONS
# -------------------------------------------------
df["PnL"] = df.apply(
    lambda x:
    (x["takeprofit"] - x["entry"]) * x["lot"]
    if x["direction"] == "Buy"
    else (x["entry"] - x["takeprofit"]) * x["lot"],
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
total_trades = len(df)
win_rate = round((df["PnL"] > 0).mean() * 100, 2)
avg_rr = round(df["RR"].mean(), 2)
net_pnl = round(df["PnL"].sum(), 2)
max_dd = round(df["Drawdown"].min(), 2)

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
    st.markdown("## Dashboard")

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: card("Trades", total_trades)
    with c2: card("Win Rate", f"{win_rate}%")
    with c3: card("Avg RR", avg_rr)
    with c4: card("Max DD", max_dd)
    with c5: card("Net PnL", net_pnl)

    fig = px.line(df, y="Equity")
    fig.update_traces(line=dict(width=3, color="#58a6ff"))
    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9",
        xaxis=dict(showgrid=False, showticklabels=False),
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
        .applymap(
            lambda v: "color:#00ff9c" if isinstance(v,(int,float)) and v > 0 else "color:#ff5c5c",
            subset=["PnL"]
        )
        .format({"PnL":"{:.2f}", "RR":"{:.2f}"}),
        use_container_width=True
    )

# -------------------------------------------------
# ANALYTICS
# -------------------------------------------------
elif page == "Analytics":
    st.markdown("## Analytics")

    dd_fig = px.area(df, y="Drawdown")
    dd_fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9"
    )
    st.plotly_chart(dd_fig, use_container_width=True)

