import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd
import os                                    # <-- add this

from src.load import load_kadaster, load_funda
from src.clean import clean_funda, clean_kadaster
from src.join import join_datasets
from src.metrics import price_stats, over_time

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Kadaster vs Funda")

# --- TEMPORARY DEBUG (delete after diagnosing) ---
st.write("CWD:", os.getcwd())
st.write("Files here:", os.listdir("."))
st.write("src exists:", os.path.exists("src"))
st.write("src contents:", os.listdir("src") if os.path.exists("src") else "N/A")
# --- END DEBUG ---

@st.cache_data
def get_kadaster():
    return clean_kadaster(load_kadaster())

@st.cache_data
def get_funda():
    return clean_funda(load_funda())

@st.cache_data
def get_joined(kad, fun):
    return join_datasets(kad, fun)

#  three error handeling cases:
#  1. Funda file not yet in data/raw/ (FileNotFoundError
#  2. Funda file missing a column (KeyError)
#  3. No matching addresses found (joined dataframe is empty)
#  makes it so that the app doesn't crash and gives the user a message about what went wrong
kad = get_kadaster()

tab1, tab2, tab3 = st.tabs(["Kadaster sales", "Funda listings", "Joined comparison"])

with tab1:
    st.subheader("Sold properties over time")
    st.plotly_chart(px.line(over_time(kad), x="year", y="Koopsom",
                            title="Median sale price per year"), use_container_width=True)
    st.dataframe(price_stats(kad))

with tab2:
    st.subheader("Funda listings — asking price per m²")
    try:
        fun = get_funda()
        st.plotly_chart(px.box(fun, x="Buurt", y="price_per_m2"),
                        use_container_width=True)
        st.dataframe(fun.head(50))
    except FileNotFoundError:
        st.info("Funda file not yet in data/raw/. Drop it in and refresh.")
    except KeyError as e:
        st.error(f"Missing column in Funda file: {e}. Check column names via "
                 f"`load_funda().columns.tolist()`")

with tab3:
    st.subheader("Sold vs asking price (matched addresses)")
    try:
        fun = get_funda()
        joined = get_joined(kad, fun)
    except FileNotFoundError:
        st.info("Funda file not yet available — joined view disabled.")
        st.stop()

    if joined.empty:
        st.warning("No matches — check the address join logic.")
    else:
        st.success(f"{len(joined)} matched addresses")
        fig = px.scatter(joined, x="Koopsom", y="Vraagprijs",
                         hover_data=[c for c in ["Street Address", "Buurt_kad", "Buurt_funda"]
                                     if c in joined.columns])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(joined.head(200))