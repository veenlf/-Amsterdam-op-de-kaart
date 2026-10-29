import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.load import load_funda
from src.clean import clean_funda, clean_cbs
from geopy.distance import geodesic

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Funda vs CBS")

@st.cache_data
@st.cache_data(show_spinner=False)
def get_data():
    fun = clean_funda(load_funda())
    
    # Load and clean the CBS data
    raw_cbs = pd.read_csv("data/raw/cbs_woningvoorraad_amsterdam.csv")
    cbs = clean_cbs(raw_cbs)
    
    # --- NEW: CALCULATE DISTANCES ---
    try:
        # Load the tram stops you generated
        stops = pd.read_csv("data/raw/tram_stops.csv")
        
        # 1. Distance to City Center (Amsterdam Centraal)
        center_loc = (52.379189, 4.899431)
        fun['dist_to_center_km'] = fun.apply(
            lambda row: geodesic(center_loc, (row['Latitude'], row['Longitude'])).km 
            if pd.notna(row['Latitude']) and pd.notna(row['Longitude']) else None, 
            axis=1
        )
        
        # 2. Distance to Nearest Stop
        def get_min_stop_distance(row):
            if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
                return None
            
            house_loc = (row['Latitude'], row['Longitude'])
            # Calculate distance to all stops and return the minimum
            distances = stops.apply(
                lambda stop: geodesic(house_loc, (stop['lat'], stop['lon'])).km, 
                axis=1
            )
            return distances.min()
        
        with st.spinner("Calculating distances to public transport (this takes a moment)..."):
            fun['dist_to_stop_km'] = fun.apply(get_min_stop_distance, axis=1)
            
    except FileNotFoundError:
        st.error("⚠️ `tram_stops.csv` not found. Please run `fetch_stops.py` to generate it.")
        fun['dist_to_center_km'] = None
        fun['dist_to_stop_km'] = None
    except Exception as e:
        st.error(f"Error calculating distances: {e}")
        
    return fun, cbs

# --- SIDEBAR FILTERS ---
# Load the data before the sidebar filters use it.
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

# ==========================================
# TAB 1: Listings & Bar Chart
# ==========================================
with tab1:
    st.subheader("Funda listings — Asking price per m²")
    
    # Filter out data missing sizes or prices for the charts
    plot_df = fun.dropna(subset=['price_per_m2', 'Buurt'])
    
    # Create two columns for the charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Distribution per Neighbourhood")
        fig = px.box(plot_df, x="Buurt", y="price_per_m2", 
                     title="Spread of Asking price per m²")
        fig.update_xaxes(showticklabels=False) 
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.markdown("### Top 10 Most Expensive Neighbourhoods")
        # Group by Buurt, calculate median price, count listings
        top_buurten = (
            plot_df.groupby('Buurt')['price_per_m2']
            .agg(['median', 'count'])
            .reset_index()
        )
        # Only keep neighbourhoods with at least 10 listings (so bars aren't empty)
        top_buurten = top_buurten[top_buurten['count'] >= 10]
        # Sort and get top 10
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
                
                # Filter to just the selected buurt
                highlight_df = map_df[map_df['Buurt'] == selected_buurt]
                
                fig = px.scatter_map(highlight_df, lat="Latitude", lon="Longitude", 
                                     size="Wonen", hover_name="Street Address", 
                                     color="Vraagprijs", color_continuous_scale="Viridis",
                                     zoom=11, height=600)
            else:
                # HEATMAP MODE: Shows where listings are densely clustered
                fig = px.density_map(map_df, lat="Latitude", lon="Longitude", 
                                     z="Vraagprijs", radius=15,
                                     zoom=11, height=600,
                                     color_continuous_scale="Inferno")
                                     
        fig.update_layout(
            map_style="carto-darkmatter", 
            margin={"r":0,"t":0,"l":0,"b":0},
            map_center={"lat": 52.3676, "lon": 4.9041}, # Centers exactly on Amsterdam
            map_zoom=10.5 # Zooms out just enough to see the whole city and the ring road
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("**Insight:** The heatmap reveals high-density clusters of expensive listings in the city centre, while the 'Specific Neighbourhood' mode lets you isolate and examine individual areas like the Jordaan or Oud-Zuid.")
    except Exception as e:
        st.error(f"Could not render map: {e}")
import scipy.stats as stats # Add this to your top-level imports

# ==========================================
# TAB 3: Statistics & Geography
# ==========================================
with tab3:
    st.subheader("Statistical Analysis: The Value of Public Transport")
    st.markdown("**Research Question:** Does proximity to a tram/metro stop increase the price per m²? And is that just because it's close to the center?")
    
    # 1. Prepare the data (using the distances we calculated)
    # Make sure you loaded 'valid_houses' with distances in your get_data() function!
    plot_df = fun.dropna(subset=['price_per_m2', 'dist_to_stop_km', 'dist_to_center_km']).copy()
    
    # 2. Create distance bands for the visual
    bins = [0, 0.3, 0.6, 1.0, 2.0, 10.0]
    labels = ['< 300m', '300m - 600m', '600m - 1km', '1km - 2km', '> 2km']
    plot_df['Distance Band'] = pd.cut(plot_df['dist_to_stop_km'], bins=bins, labels=labels)
    
    # 3. Boxplot to visualize the raw effect
    fig_box = px.box(plot_df, x='Distance Band', y='price_per_m2', 
                     title="Price per m² by Distance to Nearest Tram/Metro Stop",
                     color='Distance Band',
                     color_discrete_sequence=px.colors.sequential.Viridis)
    st.plotly_chart(fig_box, use_container_width=True)
    
    # 4. The Regression (The "Denkwerk")
    st.markdown("### Multiple Regression: Controlling for the City Center")
    st.markdown("If being close to the center is the *only* reason for high prices, the 'distance to stop' effect will disappear when we add 'distance to center' to the model.")
    
    import statsmodels.formula.api as smf
    formula = "price_per_m2 ~ dist_to_stop_km + dist_to_center_km"
    model = smf.ols(formula, data=plot_df).fit()
    
    # Display the regression table
    st.text(model.summary().tables[1])
    
    # Extract the p-value for the stop distance
    p_val_stop = model.pvalues['dist_to_stop_km']
    
    if p_val_stop < 0.05:
        st.success("**Conclusion:** Even when we control for the distance to the city center, the distance to a transport stop remains statistically significant. This proves that public transport accessibility has its own intrinsic value.")
    else:
        st.warning("**Conclusion:** Once we control for distance to the center, the distance to a transport stop is no longer significant. This suggests that the 'tram premium' is actually just a 'center premium'.")
        
    # 5. The Cycling Note (Addressing the Casus text)
    st.info(
        "**Note on Cycling:** This analysis uses straight-line distance. However, Amsterdam residents cycle. "
        "A cyclist might ignore a tram stop 200m away if it's a slow line, and instead cycle 2km to a Metro station for a faster connection. "
        "Therefore, the actual value of a transport node is likely higher than a simple straight-line distance suggests."
    )

    # 6. Address the 15 missing coordinates
    missing_coords = fun['Latitude'].isna().sum()
    if missing_coords > 0:
        st.warning(f"**Data Integrity:** {missing_coords} listings were excluded from the distance analysis because they are missing coordinates.")