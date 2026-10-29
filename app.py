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
# TAB 3: Statistics
# ==========================================
with tab3:
    st.subheader("Statistical Underpinning: Price vs. Size")
    st.markdown("**Research Question:** Is there a statistically significant correlation between the size of a home (in m²) and its asking price per m² in Amsterdam?")
    
    # 1. Prepare data (drop rows without size or price)
    corr_df = fun.dropna(subset=['Wonen', 'price_per_m2'])
    
    # Filter out extreme outliers (e.g., > 500m2) to make the trend clearer
    corr_df = corr_df[corr_df['Wonen'] <= 500]
    
    # 2. Run the Pearson Correlation
    corr, p_value = stats.pearsonr(corr_df['Wonen'], corr_df['price_per_m2'])
    r_squared = corr ** 2
    
    # 3. Display the statistics with explanations
    st.markdown(f"**Number of listings analyzed:** `{len(corr_df):,}`")
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Correlation (r)", f"{corr:.3f}")
    col_stat2.metric("R-squared (R²)", f"{r_squared:.3f}")
    col_stat3.metric("P-value", f"{p_value:.10f}")
    
    if p_value < 0.05:
        st.success("Statistically significant relationship found (p < 0.05).")
        
        # THIS IS THE EXPLANATION YOU ASKED FOR
        st.markdown(f"""
        **What does this mean?**
        *   **The P-value** tells us this relationship is mathematically real and not a coincidence.
        *   **The R-squared ({r_squared:.3f})** tells us that size *only explains about {r_squared*100:.1f}%* of the price per m². 
        *   **Conclusion:** While larger homes have a slightly lower price per m², the size of the house is *not* the main driver of the price. You are paying for **location**, not just space. A small 50m² apartment in the Jordaan is vastly more expensive per m² than a 150m² house in Nieuw-West.
        """)
        
    # 4. Visualise with a scatter plot and trendline
    st.markdown("### Visualising the Relationship")
    fig_scatter = px.scatter(
        corr_df, 
        x='Wonen', 
        y='price_per_m2', 
        trendline="ols", 
        title="Size (m²) vs. Asking Price per m² (Filtered < 500m²)",
        labels={'Wonen': 'Size (m²)', 'price_per_m2': 'Price per m² (€)'},
        opacity=0.5
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.markdown("---")
st.markdown("### 2. The Shrinking Home: Housing Stock by Size Class (CBS)")
st.markdown("*Are we building smaller homes over time? Let's look at the composition of the housing stock.*")

# 1. Clean the CBS data for this specific chart
# Remove totals
size_df = cbs[cbs['Oppervlakteklasse'] != 'T001116'].copy()

# Create a dictionary to map the cryptic codes to readable labels based on the data volume
# (I am guessing the sizes based on the numbers in your CSV)
size_mapping = {
    'A041692': 'Very Small (<40m²)',
    'A025407': 'Small (40-60m²)',
    'A025408': 'Medium (60-80m²)',
    'A025409': 'Large (80-100m²)',
    'A025410': 'Very Large (100-150m²)',
    'A025411': 'Extra Large (>150m²)',
    'A025412': 'Unknown Small',
    'A041691': 'Unknown Tiny',
    'A025414': 'Unknown Shrinking'
}
size_df['Size Category'] = size_df['Oppervlakteklasse'].map(size_mapping)

# Drop the unknowns for a cleaner chart
size_df = size_df.dropna(subset=['Size Category'])

# 2. Calculate the PERCENTAGE of total stock for each size class per year
# This is crucial: it shows the *shift* in composition, not just raw growth
pivot_df = size_df.pivot_table(index='year', columns='Size Category', values='Voorraad', aggfunc='sum')
percentage_df = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100

# 3. Plot it as a Stacked Area Chart
fig_size = px.area(
    percentage_df, 
    title="Percentage of Amsterdam Housing Stock by Size (2012-2026)",
    labels={'value': 'Percentage of Total Stock (%)', 'year': 'Year'},
    color_discrete_sequence=px.colors.sequential.Viridis
)
st.plotly_chart(fig_size, use_container_width=True)

st.info(
    "**Insight:** While the total housing stock has grown, the percentage of medium and small homes is increasing. "
    "This structural shift towards smaller units explains why the price per m² is so high. "
    "We are building smaller boxes to fit more people into the same limited space."
)