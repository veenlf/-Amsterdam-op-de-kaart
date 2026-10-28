import streamlit as st
import plotly.express as px
import pandas as pd
from src.load import load_kadaster, load_funda
from src.clean import clean_funda, clean_kadaster
from src.join import join_datasets
from src.metrics import price_stats, over_time

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Kadaster vs Funda")

@st.cache_data
def get_data():
    kad = clean_kadaster(load_kadaster())
    fun = clean_funda(load_funda())
    joined = join_datasets(kad, fun)
    return kad, fun, joined

kad, fun, joined = get_data()

# side bar filters
st.sidebar.header("Filters")
if not kad.empty and 'Datum overdracht' in kad.columns:
    min_year = int(kad['Datum overdracht'].dt.year.min())
    max_year = int(kad['Datum overdracht'].dt.year.max())
    year_range = st.sidebar.slider("Year of sale", min_year, max_year, (min_year, max_year))
    kad = kad[kad['Datum overdracht'].dt.year.between(year_range[0], year_range[1])]

#  tabs
tab1, tab2, tab3 = st.tabs(["Kadaster Sales", "Funda Map", "Sold vs Asking (Stats)"])

with tab1:
    st.subheader("Sold properties over time")
    st.plotly_chart(px.line(over_time(kad), x="year", y="Koopsom",
                            title="Median sale price per year"), use_container_width=True)
    st.dataframe(price_stats(kad))

with tab2:
    st.subheader("Funda listings — Geographic Distribution")
    try:
        # Filter out rows missing coordinates for the map
        map_df = fun.dropna(subset=['Latitude', 'Longitude'])
        # Center map on Amsterdam
        fig = px.scatter_mapbox(map_df, lat="Latitude", lon="Longitude", 
                                color="Vraagprijs", size="Wonen",
                                hover_name="Street Address", 
                                color_continuous_scale="Viridis",
                                zoom=11, height=600)
        fig.update_layout(mapbox_style="carto-darkmatter")
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Could not render map: {e}")

with tab3:
    st.subheader("Sold vs asking price (matched addresses)")
    if joined.empty:
        st.warning("No matches — check the address join logic.")
    else:
        st.success(f"{len(joined)} matched addresses")
        
        # The Statistical Analysis (Rubric Criterion 3)
        fig = px.scatter(joined, x="Koopsom", y="Vraagprijs", 
                         trendline="ols", # <--- This adds the regression line & R²
                         trendline_color_override="red",
                         hover_data=["Street Address", "Buurt_kad"])
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(joined.head(200))