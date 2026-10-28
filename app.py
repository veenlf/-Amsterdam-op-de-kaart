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
            color_by = st.radio("Map Mode:", ["Price", "Specific Neighbourhood"])
        with col2:
            if color_by == "Specific Neighbourhood":
                all_buurten = sorted(map_df['Buurt'].dropna().unique())
                selected_buurt = st.selectbox("Choose a Neighbourhood:", all_buurten)
                map_df['Highlight'] = map_df['Buurt'].apply(lambda x: x if x == selected_buurt else "Other")
                
                fig = px.scatter_map(map_df, lat="Latitude", lon="Longitude", 
                                     color="Highlight", size="Wonen",
                                     hover_name="Street Address", 
                                     color_discrete_map={selected_buurt: "red", "Other": "rgba(200, 200, 200, 0.2)"},
                                     zoom=12, height=600)
            else:
                fig = px.scatter_map(map_df, lat="Latitude", lon="Longitude", 
                                     color="Vraagprijs", size="Wonen",
                                     hover_name="Street Address", 
                                     color_continuous_scale="Viridis",
                                     zoom=12, height=600)
                                     
        fig.update_layout(
            map_style="carto-darkmatter", 
            margin={"r":0,"t":0,"l":0,"b":0},
            # THIS IS THE MAGIC FIX: Lock the map to Amsterdam's bounding box
            map_bounds=[{"lat": 52.25, "lon": 4.7}, {"lat": 52.45, "lon": 5.05}]
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Could not render map: {e}")

# ==========================================
# TAB 3: Statistics
# ==========================================
with tab3:
    st.subheader("Statistical Underpinning: City Centre vs Outskirts")
    st.markdown("We test if the asking price per m² is significantly different between the historic **Centrum** and the outer district of **Nieuw-West**.")
    
    # 1. Prepare the groups
    centrum = fun[fun['Buurt'].str.contains('Centrum', case=False, na=False)]['price_per_m2'].dropna()
    nieuwwest = fun[fun['Buurt'].str.contains('Nieuw-West', case=False, na=False)]['price_per_m2'].dropna()
    
    if len(centrum) > 0 and len(nieuwwest) > 0:
        # 2. T-test
        stat, p_value = stats.ttest_ind(centrum, nieuwwest, equal_var=False)
        
        # 3. Output results
        st.markdown(f"**Centrum:** {len(centrum)} listings, median €{centrum.median():,.0f}/m²")
        st.markdown(f"**Nieuw-West:** {len(nieuwwest)} listings, median €{nieuwwest.median():,.0f}/m²")
        st.markdown(f"**T-test p-value:** `{p_value:.10f}`")
        
        if p_value < 0.05:
            st.success("Statistically significant difference (p < 0.05).")
            st.markdown("*Conclusion: The location (Centrum vs Nieuw-West) has a statistically significant effect on the asking price per m².*")
        else:
            st.warning("No statistically significant difference found (p >= 0.05).")
            
        # 4. Boxplot visualisation
        plot_df = pd.concat([centrum, nieuwwest], keys=['Centrum', 'Nieuw-West']).reset_index()
        plot_df.columns = ['District', 'price_per_m2']
        fig = px.box(plot_df, x='District', y='price_per_m2', color='District',
                     title="Asking Price per m²: Centrum vs Nieuw-West")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data to compare Centrum vs Nieuw-West.")
        
    # 5. The CBS Trend
    st.markdown("---")
    st.markdown("### 2. Amsterdam Housing Stock (CBS) over Time")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=cbs['year'], y=cbs['Voorraad'], mode='lines+markers'))
    fig2.update_layout(title="Amsterdam Housing Stock (2012-2026)",
                      xaxis_title="Year", yaxis_title="Total Housing Stock")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.info(
        "**Conclusion:** While the housing stock has grown to 1.97 million homes, the price per m² in the Centrum is still "
        "statistically significantly higher than in Nieuw-West. This proves that simply increasing supply does not "
        "equalize prices across the city—location remains the dominant factor."
    )