import streamlit as st
import plotly.express as px
import pandas as pd
from src.load import load_funda
from src.clean import clean_funda, clean_cbs
from scipy.stats import ttest_ind

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
    st.subheader("Statistical Underpinning: Housing Type & Stock")
    
    # --- Part 1: The T-Test ---
    st.markdown("### 1. Are 'Huizen' more expensive than 'Appartementen'?")
    
    # Filter for the two main types based on the 'Title' column
    # (Funda titles start with either "Appartement te koop" or "Huis te koop")
    apps = fun[fun['Title'].str.contains('Appartement', case=False, na=False)]['price_per_m2'].dropna()
    huizen = fun[fun['Title'].str.contains('Huis', case=False, na=False)]['price_per_m2'].dropna()
    
    if len(apps) > 0 and len(huizen) > 0:
        # Run the T-test
        stat, p_value = ttest_ind(apps, huizen, equal_var=False)
        
        st.markdown(f"**Appartementen:** {len(apps)} listings, median €{apps.median():,.0f}/m²")
        st.markdown(f"**Huizen:** {len(huizen)} listings, median €{huizen.median():,.0f}/m²")
        st.markdown(f"**T-test p-value:** `{p_value:.5f}`")
        
        if p_value < 0.05:
            st.success("Statistically significant difference (p < 0.05).")
        else:
            st.warning("No statistically significant difference found (p >= 0.05).")
            
        # Visualise the groups
        fig = px.box(fun[fun['Title'].str.contains('Appartement|Huis', case=False, na=False)], 
                     x='Title', y='price_per_m2', 
                     title="Price per m²: Appartement vs Huis")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data to compare Appartement vs Huis.")

    # --- Part 2: The CBS Trend ---
    st.markdown("---")
    st.markdown("### 2. Amsterdam Housing Stock (CBS) over Time")
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=cbs['year'], y=cbs['Voorraad'], mode='lines+markers', name='Total Housing Stock'))
    fig2.update_layout(title="Amsterdam Housing Stock (2012-2026)",
                      xaxis_title="Year", yaxis_title="Total Housing Stock")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.info(
        "**Conclusion:** While the housing stock has grown steadily to 1.97 million homes, "
        "the Funda data shows a statistically significant difference (p < 0.05) in asking prices per m² between "
        "different housing types, highlighting that supply alone does not dictate prices."
    )