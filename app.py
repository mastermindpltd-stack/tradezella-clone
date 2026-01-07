import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

from auth import get_authenticator
from database import create_table, get_connection

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Trade Journal", layout="wide")

# -------------------------------------------------
# UPLOAD FOLDER (CRITICAL)
# -------------------------------------------------
UPLOAD_DIR = "uploads/screenshots"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# GLOBAL DARK UI
# -------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp { background-color: #0e1117; }
.card {
    background: linear-gradient(145deg, #161b22, #0e1117);
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
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
# NAVIGATION
# -------------------------------------------------
st.sidebar.markdown("## 📘 Trade Journal")
page = st.sidebar.radio("Navigate", ["Dashboard", "Trades", "Analytics"])

# -------------------------------------------------
# DATABASE INIT
# -------------------------------------------------
create_table()

# -------------------------------------------------
# CSV IMPORT WITH COLUMN MAPPING
# -------------------------------------------------
st.sidebar.markdown("### 📥 Import CSV")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    csv_df = pd.read_csv(uploaded_file)

    st.subheader("CSV Preview")
    st.dataframe(csv_df.head(), use_container_width=True)

    st.markdown("### 🧩 Map CSV Columns")
    pair_col = st.selectbox("Pair", csv_df.columns)
    direction_col = st.selectbox("Direction", csv_df.columns)
    entry_col = st.selectbox("Entry", csv_df.columns)
    stoploss_col = st.selectbox("Stoploss", csv_df.columns)
    takeprofit_col = st.selectbox("Takeprofit", csv_df.columns)
    lot_col = st.selectbox("Lot", csv_df.columns)

    if st.button("🚀 Import Trades"):
        conn = get_connection()
        imported, skipped = 0, 0

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

        st.success(f"Imported {imported} trades")
        if skipped:
            st.warning(f"Skipped {skipped} rows")
        st.rerun()

# -------------------------------------------------
# MANUAL ADD TRADE
# -------------------------------------------------
with st.expander("➕ Add Trade"):
    with st.form("trade_form"):
        pair = st.selectbox("Pair", ["EURUSD","GBPUSD","USDJPY","XAUUSD","BTCUSD"])
        direction = st.radio("Direction", ["Buy","Sell"], horizontal=True)

        c1, c2 = st.columns(2)
        with c1:
            entry = st.number_input("Entry", format="%.5f")
            stoploss = st.number_input("Stoploss", format="%.5f")
        with c2:
            takeprofit = st.number_input("Takeprofit", format="%.5f")
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
        st.rerun()

# -------------------------------------------------
# LOAD TRADES
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
# CALCULATIONS (FIXED)
# -------------------------------------------------
df["PnL"] = df.apply(
    lambda r:
    (r["takeprofit"] - r["entry"]) * r["lot"]
    if r["direction"] == "Buy"
    else (r["entry"] - r["takeprofit"]) * r["lot"],
    axis=1
)

df["Risk"] = (df["entry"] - df["stoploss"]).abs() * df["lot"]
df["Reward"] = (df["takeprofit"] - df["entry"]).abs() * df["lot"]
df["RR"] = (df["Reward"] / df["Risk"]).round(2)

df["Equity"] = df["PnL"].cumsum()
df["Peak"] = df["Equity"].cummax()
df["Drawdown"] = df["Equity"] - df["Peak"]

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
if page == "Dashboard":
    st.markdown("## Dashboard")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Trades", len(df))
    c2.metric("Win Rate", f"{round((df['PnL']>0).mean()*100,2)}%")
    c3.metric("Avg RR", round(df["RR"].mean(),2))
    c4.metric("Max DD", round(df["Drawdown"].min(),2))
    c5.metric("Net PnL", round(df["PnL"].sum(),2))

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
# TRADES + SCREENSHOT UPLOAD
# -------------------------------------------------
elif page == "Trades":
    st.markdown("## Trades")
    st.dataframe(df, use_container_width=True)

    st.markdown("## 📸 Screenshot Review")

    trade_id = st.selectbox("Select Trade ID", df["id"].tolist())
    uploaded_img = st.file_uploader("Upload Screenshot", type=["png","jpg","jpeg"])
    notes = st.text_area("Trade Notes")

    if st.button("💾 Save Screenshot"):
        if uploaded_img is None:
            st.error("Please upload an image")
        else:
            filename = f"{username}_{trade_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            filepath = os.path.join(UPLOAD_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(uploaded_img.getbuffer())

            conn = get_connection()
            conn.execute(
                "UPDATE trades SET screenshot = ?, notes = ? WHERE id = ?",
                (filepath, notes, trade_id)
            )
            conn.commit()
            conn.close()

            st.success("Screenshot saved")
            st.rerun()

    review = df[df["id"] == trade_id].iloc[0]
    if review["screenshot"]:
        st.image(review["screenshot"], use_column_width=True)
    if review["notes"]:
        st.info(review["notes"])

# -------------------------------------------------
# ANALYTICS
# -------------------------------------------------
elif page == "Analytics":
    st.markdown("## Analytics")
    fig = px.area(df, y="Drawdown")
    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9"
    )
    st.plotly_chart(fig, use_container_width=True)
