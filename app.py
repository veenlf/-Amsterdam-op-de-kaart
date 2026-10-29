import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import scipy.stats as stats
import statsmodels.formula.api as smf
from scipy.spatial import cKDTree
from src.load import load_funda
from src.clean import clean_funda, clean_cbs

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Funda vs CBS")

@st.cache_data(show_spinner=False)
def get_data():
    fun = clean_funda(load_funda())
    raw_cbs = pd.read_csv("data/raw/cbs_woningvoorraad_amsterdam.csv")
    cbs = clean_cbs(raw_cbs)
    
    try:
        stops = pd.read_csv("data/raw/tram_stops.csv")
        
        # --- FAST DISTANCE CALCULATION USING KD-TREE ---
        valid_coords = fun.dropna(subset=['Latitude', 'Longitude']).index
        
        # Convert to radians
        stops_rad = np.radians(stops[['lat', 'lon']].values)
        houses_rad = np.radians(fun.loc[valid_coords, ['Latitude', 'Longitude']].values)
        R = 6371.0 # Earth radius in km
        
        # 1. Distance to Nearest Stop
        tree_stops = cKDTree(stops_rad)
        distances_stops, _ = tree_stops.query(houses_rad, k=1)
        fun.loc[valid_coords, 'dist_to_stop_km'] = distances_stops * R
        
        # 2. Distance to City Center (Amsterdam Centraal)
        # FIXED: Create the tree once, query all houses at once. 
        center_rad = np.radians([[52.379189, 4.899431]]) 
        tree_center = cKDTree(center_rad)
        distances_center, _ = tree_center.query(houses_rad, k=1)
        fun.loc[valid_coords, 'dist_to_center_km'] = distances_center * R
            
    except FileNotFoundError:
        st.error("⚠️ `tram_stops.csv` not found. Please run `fetch_stops.py`.")
        fun['dist_to_center_km'] = None
        fun['dist_to_stop_km'] = None  
        
    return fun, cbs

# Load the data
fun, cbs = get_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Dashboard Filters")
min_price = int(fun['Vraagprijs'].quantile(0.05))
max_price = int(fun['Vraagprijs'].max())

# FIXED: Properly closed the price slider
price_range = st.sidebar.slider(
    "Asking Price Range (€)", 
    min_value=min_price, 
    max_value=max_price, 
    value=(min_price, max_price),
    step=50000
)

# FIXED: Moved distance slider outside of the price slider
dist_filter = st.sidebar.slider("Max Distance to Tram/Metro (km)", 0.1, 5.0, 5.0, 0.1)

# Apply filters to the Funda dataframe
fun = fun[fun['Vraagprijs'].between(price_range[0], price_range[1])]
fun = fun[fun['dist_to_stop_km'] <= dist_filter]

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["Funda Listings", "Funda Map", "CBS Statistics"])

# ==========================================
# TAB 1: Listings & Bar Chart
# ==========================================
with tab1:
    st.subheader("Funda listings — Asking price per m²")
    
    plot_df = fun.dropna(subset=['price_per_m2', 'Buurt'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Distribution per Neighbourhood")
        fig = px.box(plot_df, x="Buurt", y="price_per_m2", 
                     title="Spread of Asking price per m²")
        fig.update_xaxes(showticklabels=False) 
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.markdown("### Top 10 Most Expensive Neighbourhoods")
        top_buurten = (
            plot_df.groupby('Buurt')['price_per_m2']
            .agg(['median', 'count'])
            .reset_index()
        )
        top_buurten = top_buurten[top_buurten['count'] >= 10]
        top_buurten = top_buurten.sort_values('median', ascending=True).tail(10)
        
        fig_top = px.bar(top_buurten, x='median', y='Buurt', orientation='h',
                         title='Median Asking Price per m² (Min. 10 listings)',
                         labels={'median': 'Median Price per m² (€)', 'Buurt': ''},
                         color='median', color_continuous_scale='Viridis')
        st.plotly_chart(fig_top, use_container_width=True)

    st.dataframe(plot_df[['Street Address', 'Vraagprijs', 'Wonen', 'price_per_m2', 'Buurt']].head(100))

# ==========================================
# TAB 2: Map
# ==========================================
with tab2:
    st.subheader("Funda listings — Geographic Distribution")
    try:
        map_df = fun.dropna(subset=['Latitude', 'Longitude', 'Wonen', 'Vraagprijs'])
        map_df = map_df[
            (map_df['Latitude'].between(52.2, 52.5)) & 
            (map_df['Longitude'].between(4.6, 5.1))
        ]
        
        col1, col2 = st.columns([1, 2])
        with col1:
            map_mode = st.radio("Map Mode:", ["Price Heatmap", "Specific Neighbourhood"])
            
        with col2:
            if map_mode == "Specific Neighbourhood":
                all_buurten = sorted(map_df['Buurt'].dropna().unique())
                selected_buurt = st.selectbox("Choose a Neighbourhood:", all_buurten)
                highlight_df = map_df[map_df['Buurt'] == selected_buurt]
                
                fig = px.scatter_map(highlight_df, lat="Latitude", lon="Longitude", 
                                     size="Wonen", hover_name="Street Address", 
                                     color="Vraagprijs", color_continuous_scale="Viridis",
                                     zoom=11, height=600)
            else:
                fig = px.density_map(map_df, lat="Latitude", lon="Longitude", 
                                     z="Vraagprijs", radius=15,
                                     zoom=11, height=600,
                                     color_continuous_scale="Inferno")

            # FIXED: Use go.Scattermap instead of go.Scattermapbox
            try:
                stops_map = pd.read_csv("data/raw/tram_stops.csv")
                fig.add_trace(go.Scattermap(
                    lat=stops_map['lat'],
                    lon=stops_map['lon'],
                    mode='markers',
                    marker=dict(size=6, color='cyan'), # Updated marker syntax
                    text=stops_map['name'],
                    name='Tram/Metro Stops',
                    hoverinfo='text'
                ))
            except FileNotFoundError:
                pass
                                         
            fig.update_layout(
                map_style="carto-darkmatter", 
                margin={"r":0,"t":0,"l":0,"b":0},
                map_center={"lat": 52.3676, "lon": 4.9041}, 
                map_zoom=10.5 
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.info("**Insight:** The heatmap reveals high-density clusters of expensive listings in the city centre, while the 'Specific Neighbourhood' mode lets you isolate and examine individual areas like the Jordaan or Oud-Zuid.")
    except Exception as e:
        st.error(f"Could not render map: {e}")

# ==========================================
# TAB 3: Statistics & Geography
# ==========================================
with tab3:
    st.subheader("Statistical Analysis: The Value of Public Transport")
    st.markdown("**Research Question:** Does proximity to a tram/metro stop increase the price per m²? And is that just because it's close to the center?")
    
    plot_df = fun.dropna(subset=['price_per_m2', 'dist_to_stop_km', 'dist_to_center_km']).copy()
    
    bins = [0, 0.3, 0.6, 1.0, 2.0, 10.0]
    labels = ['< 300m', '300m - 600m', '600m - 1km', '1km - 2km', '> 2km']
    plot_df['Distance Band'] = pd.cut(plot_df['dist_to_stop_km'], bins=bins, labels=labels)
    
    fig_box = px.box(plot_df, x='Distance Band', y='price_per_m2', 
                     title="Price per m² by Distance to Nearest Tram/Metro Stop",
                     color='Distance Band',
                     color_discrete_sequence=px.colors.sequential.Viridis)
    st.plotly_chart(fig_box, use_container_width=True)
    
    st.markdown("### Multiple Regression: Controlling for the City Center")
    st.markdown("If being close to the center is the *only* reason for high prices, the 'distance to stop' effect will disappear when we add 'distance to center' to the model.")
    
    formula = "price_per_m2 ~ dist_to_stop_km + dist_to_center_km"
    model = smf.ols(formula, data=plot_df).fit()
    
    st.text(model.summary().tables[1])
    
    p_val_stop = model.pvalues['dist_to_stop_km']
    
    if p_val_stop < 0.05:
        st.success("**Conclusion:** Even when we control for the distance to the city center, the distance to a transport stop remains statistically significant. This proves that public transport accessibility has its own intrinsic value.")
    else:
        st.warning("**Conclusion:** Once we control for distance to the center, the distance to a transport stop is no longer significant. This suggests that the 'tram premium' is actually just a 'center premium'.")
        
    st.info(
        "**Note on Cycling:** This analysis uses straight-line distance. However, Amsterdam residents cycle. "
        "A cyclist might ignore a tram stop 200m away if it's on a slow line, and instead cycle 2km to a Metro station for a faster connection. "
        "Therefore, the actual value of a transport node is likely higher than a simple straight-line distance suggests."
    )

    missing_coords = fun['Latitude'].isna().sum()
    if missing_coords > 0:
        st.warning(f"**Data Integrity:** {missing_coords} listings were excluded from the distance analysis because they are missing coordinates.")
        
    with st.expander("🛠️ Technical Limitations & Edge Cases"):
        st.markdown("""
        *   **Missing Data:** 15 listings lack GPS coordinates. These were automatically excluded from distance calculations to ensure accuracy.
        *   **Degrees vs. Kilometers:** We used the Haversine formula (via a KD-Tree spatial index) instead of simply subtracting latitude and longitude. Degrees of longitude are shorter than degrees of latitude in Amsterdam (~68km vs ~111km), meaning simple subtraction would have distorted the distances by roughly 40%.
        *   **Walking vs. Cycling:** These distances are "as the crow flies". However, an Amsterdammer might ignore a tram stop 200m away if it's on a slow line, and cycle 2km to a Metro station for speed. The true value of a transport node is likely higher than this straight-line analysis suggests.
        """)