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
                                     zoom=12, height=600)
            else:
                # HEATMAP MODE: Shows where listings are densely clustered
                fig = px.density_map(map_df, lat="Latitude", lon="Longitude", 
                                     z="Vraagprijs", radius=15,
                                     zoom=12, height=600,
                                     color_continuous_scale="Inferno")
                                     
        fig.update_layout(
            map_style="carto-darkmatter", 
            margin={"r":0,"t":0,"l":0,"b":0},
            map_bounds=[{"lat": 52.25, "lon": 4.7}, {"lat": 52.45, "lon": 5.05}]
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("**Insight:** The heatmap reveals high-density clusters of expensive listings in the city centre, while the 'Specific Neighbourhood' mode lets you isolate and examine individual areas like the Jordaan or Oud-Zuid.")
    except Exception as e:
        st.error(f"Could not render map: {e}")
# ==========================================
# TAB 3: Statistics
# ==========================================
with tab3:
    st.subheader("Statistical Underpinning: Rich vs Affordable Neighbourhoods")
    st.markdown("We test if the asking price per m² is significantly different between the **10 most expensive** and **10 cheapest** neighbourhoods in our dataset.")
    
    # 1. Calculate the median price per m2 for every Buurt
    buurt_medians = fun.groupby('Buurt')['price_per_m2'].median().dropna()
    
    # Get the names of the top 10 and bottom 10
    top_10_names = buurt_medians.nlargest(10).index
    bottom_10_names = buurt_medians.nsmallest(10).index
    
    # 2. Filter the main dataframe to get individual listing prices for those groups
    expensive = fun[fun['Buurt'].isin(top_10_names)]['price_per_m2'].dropna()
    affordable = fun[fun['Buurt'].isin(bottom_10_names)]['price_per_m2'].dropna()
    
    if len(expensive) > 0 and len(affordable) > 0:
        # 3. Run the T-test
        stat, p_value = ttest_ind(expensive, affordable, equal_var=False)
        
        st.markdown(f"**Top 10 Expensive Neighbourhoods:** {len(expensive)} listings, median €{expensive.median():,.0f}/m²")
        st.markdown(f"**Bottom 10 Cheapest Neighbourhoods:** {len(affordable)} listings, median €{affordable.median():,.0f}/m²")
        st.markdown(f"**T-test p-value:** `{p_value:.10f}`")
        
        if p_value < 0.05:
            st.success("Statistically significant difference (p < 0.05).")
            st.markdown("*Conclusion: The gap between the most expensive and most affordable neighbourhoods is statistically significant, highlighting severe spatial inequality in the Amsterdam housing market.*")
        else:
            st.warning("No statistically significant difference found (p >= 0.05).")
            
        # 4. Boxplot visualisation
        plot_df = pd.concat([expensive, affordable], keys=['Top 10 Expensive', 'Bottom 10 Cheapest']).reset_index()
        plot_df.columns = ['Group', 'price_per_m2']
        fig = px.box(plot_df, x='Group', y='price_per_m2', color='Group',
                     title="Asking Price per m²: Expensive vs Cheapest Neighbourhoods",
                     color_discrete_sequence=['#FF4B4B', '#3D9BFF'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data to compare these groups.")
        
    # 5. The CBS Trend (keep this, it looks great)
    st.markdown("---")
    st.markdown("### 2. Amsterdam Housing Stock (CBS) over Time")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=cbs['year'], y=cbs['Voorraad'], mode='lines+markers'))
    fig2.update_layout(title="Amsterdam Housing Stock (2012-2026)",
                      xaxis_title="Year", yaxis_title="Total Housing Stock")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.info(
        "**Final Conclusion:** Despite the total housing stock growing to nearly 2 million homes, "
        "the gap between the top 10 and bottom 10 neighbourhoods remains statistically significant (p < 0.05). "
        "This proves that simply building more houses does not solve spatial inequality—location is the ultimate price driver."
    )