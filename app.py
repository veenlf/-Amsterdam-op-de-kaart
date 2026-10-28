import streamlit as st
import plotly.express as px
import pandas as pd
from src.load import load_kadaster, load_funda
from src.clean import clean_funda, clean_kadaster, clean_cbs
from src.join import join_datasets
from src.metrics import price_stats, over_time

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Kadaster vs Funda")

@st.cache_data
def get_data():
    kad = clean_kadaster(load_kadaster())
    fun = clean_funda(load_funda())
    
    # Load and clean the CBS data
    raw_cbs = pd.read_csv("data/raw/cbs_woningvoorraad_amsterdam.csv")
    cbs = clean_cbs(raw_cbs)
    
    joined = join_datasets(kad, fun)
    return kad, fun, joined, cbs

kad, fun, joined, cbs = get_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")
if not kad.empty and 'Datum overdracht' in kad.columns:
    min_year = int(kad['Datum overdracht'].dt.year.min())
    max_year = int(kad['Datum overdracht'].dt.year.max())
    year_range = st.sidebar.slider("Year of sale", min_year, max_year, (min_year, max_year))
    kad_filtered = kad[kad['Datum overdracht'].dt.year.between(year_range[0], year_range[1])]
else:
    kad_filtered = kad

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["Kadaster Sales", "Funda Map", "Sold vs Asking", "CBS Statistics"])

with tab1:
    st.subheader("Sold properties over time")
    st.plotly_chart(px.line(over_time(kad_filtered), x="year", y="Koopsom",
                            title="Median sale price per year"), use_container_width=True)
    st.dataframe(price_stats(kad_filtered))

with tab2:
    st.subheader("Funda listings — Geographic Distribution")
    try:
        map_df = fun.dropna(subset=['Latitude', 'Longitude', 'Wonen', 'Vraagprijs'])
        fig = px.scatter_map(map_df, lat="Latitude", lon="Longitude", 
                             color="Vraagprijs", size="Wonen",
                             hover_name="Street Address", 
                             color_continuous_scale="Viridis",
                             zoom=11, height=600,
                             center={"lat": 52.3676, "lon": 4.9041})
        fig.update_layout(map_style="carto-darkmatter")
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
        fig = px.scatter(joined, x="Koopsom", y="Vraagprijs", 
                         trendline="ols",
                         trendline_color_override="red",
                         hover_data=["Street Address", "Buurt_kad"])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(joined.head(200))

with tab4:
    st.subheader("Statistical Underpinning: Price vs Housing Stock")
    
    # 1. Get the median price per year
    price_over_time = over_time(kad_filtered)
    
    # 2. Merge with CBS housing stock on 'year'
    merged_stats = pd.merge(price_over_time, cbs, on="year", how="inner")
    
    if merged_stats.empty:
        st.warning("No overlapping years between Kadaster and CBS data to correlate.")
    else:
        # 3. Calculate Pearson correlation
        correlation = merged_stats['Koopsom'].corr(merged_stats['Voorraad'])
        
        st.markdown(f"**Pearson Correlation (r):** `{correlation:.3f}`")
        st.markdown("*(A value close to 1.0 indicates a strong positive relationship, meaning prices tend to rise as the number of homes increases.)*")
        
        # 4. Plot the dual-axis chart
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Line 1: Median Price
        fig.add_trace(
            go.Scatter(x=merged_stats['year'], y=merged_stats['Koopsom'], name="Median Sale Price", mode="lines+markers"),
            secondary_y=False,
        )
        
        # Line 2: Housing Stock
        fig.add_trace(
            go.Scatter(x=merged_stats['year'], y=merged_stats['Voorraad'], name="Housing Stock", mode="lines+markers"),
            secondary_y=True,
        )
        
        fig.update_layout(title="Amsterdam: Median Price vs Housing Stock")
        fig.update_xaxes(title_text="Year")
        fig.update_yaxes(title_text="Median Price (€)", secondary_y=False)
        fig.update_yaxes(title_text="Total Housing Stock", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)