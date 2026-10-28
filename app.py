import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
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

# --- SIDEBAR FILTERS ---
st.sidebar.header("Dashboard Filters")
min_price = int(fun['Vraagprijs'].min())
max_price = int(fun['Vraagprijs'].max())
price_range = st.sidebar.slider(
    "Asking Price Range (€)", 
    min_value=min_price, 
    max_value=max_price, 
    value=(min_price, max_price),
    step=50000
)

# Apply the filter to the Funda dataframe
fun = fun[fun['Vraagprijs'].between(price_range[0], price_range[1])]

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["Funda Listings", "Funda Map", "CBS Statistics"])

with tab1:
    st.subheader("Funda listings — Asking price per m²")
    fig = px.box(fun, x="Buurt", y="price_per_m2", 
                 title="Asking price per m² by Buurt")
    fig.update_xaxes(showticklabels=False) 
    st.plotly_chart(fig, use_container_width=True)
    
    # --- NEW: Top 10 Neighbourhoods ---
    st.subheader("Top 10 Most Expensive Neighbourhoods")
    
    # Calculate median price per m2 for each Buurt, sort, and get top 10
    top_buurten = (
        fun.groupby('Buurt')['price_per_m2']
        .median()
        .sort_values(ascending=True) # Ascending so the highest is at the top of the horizontal chart
        .tail(10)
        .reset_index()
    )
    
    fig_top = px.bar(top_buurten, x='price_per_m2', y='Buurt', orientation='h',
                     title='Median Asking Price per m² (Top 10)',
                     labels={'price_per_m2': 'Median Price per m² (€)', 'Buurt': ''})
    st.plotly_chart(fig_top, use_container_width=True)
    
    st.dataframe(fun[['Street Address', 'Vraagprijs', 'Wonen', 'price_per_m2', 'Buurt']].head(100))

with tab2:
    st.subheader("Funda listings — Geographic Distribution")
    try:
        map_df = fun.dropna(subset=['Latitude', 'Longitude', 'Wonen', 'Vraagprijs'])
        
        # Dropdown to choose what the map colors by
        color_by = st.selectbox("Color listings by:", ["Vraagprijs", "Buurt"])
        
        # If coloring by neighbourhood, we use a categorical map
        if color_by == "Buurt":
            fig = px.scatter_map(map_df, lat="Latitude", lon="Longitude", 
                                 color=color_by, size="Wonen",
                                 hover_name="Street Address", 
                                 zoom=11, height=600,
                                 center={"lat": 52.3676, "lon": 4.9041})
        else:
            # If coloring by price, use the continuous Viridis scale
            fig = px.scatter_map(map_df, lat="Latitude", lon="Longitude", 
                                 color=color_by, size="Wonen",
                                 hover_name="Street Address", 
                                 color_continuous_scale="Viridis",
                                 zoom=11, height=600,
                                 center={"lat": 52.3676, "lon": 4.9041})
                                 
        fig.update_layout(map_style="carto-darkmatter")
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("**Insight:** Toggle the view to see how the most expensive listings cluster in specific neighbourhoods (like Centrum and Oud-Zuid) rather than being evenly spread.")
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
    # Create a clean label for the X-axis
        fun['Type'] = fun['Title'].apply(lambda x: 'Appartement' if 'Appartement' in str(x) else 'Huis')
    
    # Filter only Appartement and Huis
        plot_df = fun[fun['Type'].isin(['Appartement', 'Huis'])]
    
        fig = px.box(plot_df, x='Type', y='price_per_m2', 
                 title="Price per m²: Appartement vs Huis",
                 color='Type')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data to compare Appartement vs Huis.")

#   The CBS Trend 
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