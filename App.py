import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os, csv
from datetime import datetime
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# =====================
# LOAD ENV
# =====================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =====================
# CONFIG
# =====================
URL = "https://www.logammulia.com/id/purchase/gold"
HEADERS = {"User-Agent": "Mozilla/5.0"}
GRAM_LIST = ["0.5 gr", "1 gr", "2 gr", "3 gr", "5 gr", "10 gr"]
LOG_FILE = "stock_log.csv"

# =====================
# TELEGRAM
# =====================
def send_telegram(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(api, data=payload, timeout=10)

# =====================
# CHECK STOCK
# =====================
def check_stock():
    r = requests.get(URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.find_all("div", class_="product-item")
    result = {}
    for gram in GRAM_LIST:
        available = False
        for card in cards:
            text = card.get_text(" ").lower()
            if gram.replace(" ", "") in text.replace(" ", ""):
                if "belum tersedia" not in text:
                    available = True
                break
        result[gram] = available
    return result

# =====================
# LOG CSV
# =====================
def log_stock(status):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["timestamp", "gram", "status"])
        for g, a in status.items():
            w.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                g,
                "TERSEDIA" if a else "HABIS"
            ])

# =====================
# STREAMLIT CONFIG
# =====================
st.set_page_config(page_title="Antam Gold Monitor", page_icon="🪙", layout="centered")

# =====================
# HEADER
# =====================
st.markdown("""
<div style="padding:16px;border-radius:12px;background:linear-gradient(90deg,#1f2937,#111827);color:white">
<h2>🪙 Antam Gold Stock Monitor</h2>
<p>Auto update • Telegram alert • Local monitoring • Framer Embed</p>
</div>
""", unsafe_allow_html=True)

# =====================
# AUTO REFRESH
# =====================
refresh_min = st.slider("⏱️ Auto update (menit)", 1, 30, 5, key="refresh_slider")
st_autorefresh(interval=refresh_min*60*1000, key="auto")

# =====================
# FAVORITE GRAM
# =====================
favorite = st.multiselect("⭐ Gram favorit", GRAM_LIST, default=["1 gr", "5 gr"])

# =====================
# STATE
# =====================
if "last_status" not in st.session_state:
    st.session_state.last_status = {}

# =====================
# MAIN CHECK STOCK
# =====================
status = check_stock()
log_stock(status)

available_count = sum([1 if a else 0 for a in status.values()])

# =====================
# SUMMARY
# =====================
m1, m2, m3 = st.columns(3)
m1.metric("Total Produk", len(status))
m2.metric("Tersedia", available_count)
m3.metric("Habis", len(status) - available_count)

# =====================
# STATUS GRID
# =====================
st.subheader("📦 Status Stok")
cols = st.columns(3)
for i, (gram, available) in enumerate(status.items()):
    with cols[i%3]:
        # Header card
        h1, h2 = st.columns([4,1])
        with h1:
            st.markdown(f"**{gram}**")
        with h2:
            if gram in favorite:
                st.markdown("⭐")
        # Status
        if available:
            st.success("🟢 TERSEDIA")
        else:
            st.error("🔴 HABIS")
        # Telegram alert
        last = st.session_state.last_status.get(gram, False)
        if available and not last:
            send_telegram(f"🚨 EMAS ANTAM TERSEDIA\nBerat: {gram}\n{URL}")
            st.toast("🔔 Stok tersedia!", icon="🔊")

st.session_state.last_status = status
st.caption(f"🕒 Update: {datetime.now():%d %b %Y • %H:%M:%S}")

# =====================
# LOG TABLE & GRAFIK
# =====================
st.divider()
st.subheader("📈 Grafik Ketersediaan")

if os.path.exists(LOG_FILE):
    df = pd.read_csv(LOG_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    chart = df.groupby("timestamp")["status"].apply(lambda x: (x=="TERSEDIA").sum()).reset_index()
    st.line_chart(chart.rename(columns={"timestamp":"index", "status":"TERSEDIA"}).set_index("index"))
else:
    st.info("Belum ada data grafik.")

with st.expander("📜 Detail Log"):
    if os.path.exists(LOG_FILE):
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Belum ada log.")

# =====================
# TEST TELEGRAM
# =====================
if st.button("🔔 Test Telegram"):
    send_telegram("✅ TEST BERHASIL\nBot Telegram aktif.")
    st.success("Pesan test terkirim")

