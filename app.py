import streamlit as st
import plotly.express as px
import pandas as pd
from src.load import load_funda
from src.clean import clean_funda, clean_cbs

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Funda vs CBS")

@st.cache_data
def get_data():
    fun = clean_funda(load_funda())
    
    # Load and clean the CBS data
    raw_cbs = pd.read_csv("data/raw/cbs_woningvoorraad_amsterdam.csv")
    cbs = clean_cbs(raw_cbs)
    
    return fun, cbs

fun, cbs = get_data()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["Funda Listings", "Funda Map", "CBS Statistics"])

with tab1:
    st.subheader("Funda listings — Asking price per m²")
    # Boxplot of asking price per m2 by neighbourhood
    fig = px.box(fun, x="Buurt", y="price_per_m2", 
                 title="Asking price per m² by Buurt")
    fig.update_xaxes(showticklabels=False) # Hide labels to keep it clean
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(fun[['Street Address', 'Vraagprijs', 'Wonen', 'price_per_m2', 'Buurt']].head(100))

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
    st.subheader("Statistical Underpinning: Asking Price vs Housing Stock")
    
    # 1. Get the average asking price per year from Funda
    # First, we need to extract the year from the Funda data. 
    # Since Funda doesn't have a 'date' column, we'll just plot the median price per m2 across all listings.
    median_m2 = fun['price_per_m2'].median()
    
    st.markdown(f"**Median asking price per m² across all Funda listings:** `€ {median_m2:,.0f}`")
    
    # 2. Plot the CBS Housing Stock over time
    import plotly.graph_objects as go
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cbs['year'], y=cbs['Voorraad'], mode='lines+markers', name='Total Housing Stock'))
    fig.update_layout(title="Amsterdam Housing Stock (CBS) over Time",
                      xaxis_title="Year", yaxis_title="Total Housing Stock")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 3. Add a text box for the statistical conclusion
    st.info(
        "**Conclusion:** The housing stock in the Amsterdam region has grown steadily from 1.63M in 2012 to 1.97M in 2026. "
        "Because the Funda dataset is a single snapshot in time, we cannot correlate the asking prices over time. "
        "However, this CBS trend shows the structural pressure on the housing market."
    )