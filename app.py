import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import scipy.stats as stats
import statsmodels.formula.api as smf
from scipy.spatial import cKDTree
from src.load import load_funda
from src.clean import clean_funda

st.set_page_config(page_title="Amsterdam Housing — Case 2", layout="wide")
st.title("Amsterdam Housing Prices — Funda vs CBS")

R = 6371.0
CENTRAAL = (52.379189, 4.899431)

def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

def chord(km):  # km radius -> chord length on the unit sphere (for the KD-tree)
    return 2 * np.sin(km / (2 * R))

@st.cache_data(show_spinner=False)
def get_data():
    raw = load_funda()
    n_raw = len(raw)
    coords = raw[["Latitude", "Longitude"]].apply(pd.to_numeric, errors="coerce")
    n_missing_coords = int(coords.isna().any(axis=1).sum())

    fun = clean_funda(raw)
    stops = pd.read_csv("data/raw/tram_stops.csv")  # no try/except: fail loudly

    houses = np.radians(fun[["Latitude", "Longitude"]].values)
    tree = cKDTree(np.radians(stops[["lat", "lon"]].values))

    d_chord, _ = tree.query(houses, k=1)
    fun["dist_to_stop_km"] = 2 * R * np.arcsin(d_chord / 2)   # exact arc length
    fun["stops_500m"] = tree.query_ball_point(houses, r=chord(0.5), return_length=True)
    fun["stops_2km"] = tree.query_ball_point(houses, r=chord(2.0), return_length=True)
    fun["dist_to_center_km"] = haversine_km(fun["Latitude"], fun["Longitude"], *CENTRAAL)
    return fun, n_raw, n_missing_coords

fun, n_raw, n_missing_coords = get_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Dashboard Filters")
p_min, p_max = int(fun["Vraagprijs"].min()), int(fun["Vraagprijs"].max())
price_range = st.sidebar.slider("Asking Price Range (€)", p_min, p_max, (p_min, p_max), step=50000)
d_max = float(np.ceil(fun["dist_to_stop_km"].max()))
dist_filter = st.sidebar.slider("Max distance to tram/metro stop (km)", 0.1, d_max, d_max, 0.1)
stadsdelen = sorted(fun["Stadsdeel"].dropna().unique())
chosen = st.sidebar.multiselect("Stadsdeel", stadsdelen, default=stadsdelen)

fun = fun[
    fun["Vraagprijs"].between(*price_range)
    & (fun["dist_to_stop_km"] <= dist_filter)
    & fun["Stadsdeel"].isin(chosen)
]
if fun.empty:
    st.warning("No listings match these filters. Widen them in the sidebar.")
    st.stop()


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
                fig = px.scatter_map(
                    map_df, lat="Latitude", lon="Longitude",
                    color="price_per_m2", color_continuous_scale="Viridis",
                    range_color=[map_df["price_per_m2"].quantile(0.05), map_df["price_per_m2"].quantile(0.95)],
                    hover_name="Street Address", opacity=0.6, zoom=11, height=600,
                    labels={"price_per_m2": "€/m²"},
                )
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
    st.subheader("The value of public transport: stop proximity vs. centre proximity")

    plot_df = fun.dropna(subset=["price_per_m2", "dist_to_stop_km", "dist_to_center_km", "Stadsdeel"]).copy()
    if len(plot_df) < 30:
        st.warning("Too few listings left for a reliable analysis. Widen the filters.")
        st.stop()

    # 1) Distance bands
    bins = [0, 0.3, 0.6, 1.0, 2.0, 100]
    labels = ["< 300m", "300–600m", "600m–1km", "1–2km", "> 2km"]
    plot_df["Distance Band"] = pd.cut(plot_df["dist_to_stop_km"], bins=bins, labels=labels)
    st.plotly_chart(px.box(plot_df, x="Distance Band", y="price_per_m2", color="Distance Band",
                           category_orders={"Distance Band": labels},
                           title="Price per m² by distance to nearest stop"), use_container_width=True)

    # 2) Same distance to centre, near vs far from a stop
    st.markdown("### Is it the stop, or the centre?")
    plot_df["Centre band"] = pd.cut(plot_df["dist_to_center_km"], [0, 2, 4, 6, 10, 100],
                                    labels=["< 2 km", "2–4 km", "4–6 km", "6–10 km", "> 10 km"])
    plot_df["Near a stop (< 500 m)"] = plot_df["dist_to_stop_km"] < 0.5
    within = (plot_df.groupby(["Centre band", "Near a stop (< 500 m)"], observed=True)["price_per_m2"]
              .agg(median="median", n="count").reset_index())
    st.plotly_chart(px.bar(within, x="Centre band", y="median", color="Near a stop (< 500 m)",
                           barmode="group", hover_data=["n"],
                           title="Median €/m² at the same distance from the centre"), use_container_width=True)

    # 3) Regression: three models
    r = plot_df[["dist_to_stop_km", "dist_to_center_km"]].corr().iloc[0, 1]
    st.caption(f"Correlation between distance-to-stop and distance-to-centre: {r:.2f}. "
               "High values make it hard to separate the two effects.")
    models = {
        "Stop only": smf.ols("price_per_m2 ~ dist_to_stop_km", plot_df).fit(),
        "+ centre distance": smf.ols("price_per_m2 ~ dist_to_stop_km + dist_to_center_km", plot_df).fit(),
        "+ centre + stadsdeel": smf.ols("price_per_m2 ~ dist_to_stop_km + dist_to_center_km + C(Stadsdeel)", plot_df).fit(),
    }
    rows = []
    for name, m in models.items():
        lo, hi = m.conf_int().loc["dist_to_stop_km"]
        rows.append({"Model": name,
                     "€/m² per extra km to a stop": round(m.params["dist_to_stop_km"]),
                     "95% CI": f"{lo:.0f} to {hi:.0f}",
                     "p-value": f"{m.pvalues['dist_to_stop_km']:.3g}",
                     "R²": round(m.rsquared, 2), "n": int(m.nobs)})
    st.table(pd.DataFrame(rows))

    m2 = models["+ centre distance"]
    b, p = m2.params["dist_to_stop_km"], m2.pvalues["dist_to_stop_km"]
    if p >= 0.05:
        st.warning(f"**Conclusion:** after controlling for centre distance, distance to a stop is not significant "
                   f"(p = {p:.2f}). The 'stop premium' is mostly a 'centre premium'.")
    elif b < 0:
        st.success(f"**Conclusion:** at the same distance from the centre, every km closer to a stop goes with "
                   f"about €{abs(b):.0f}/m² higher asking prices (R² = {m2.rsquared:.2f}, n = {int(m2.nobs)}).")
    else:
        st.warning(f"**Conclusion:** after controlling for centre distance, being farther from a stop goes with "
                   f"€{b:.0f}/m² higher prices. Proximity to a stop does not carry its own premium here. "
                   "Association only, not causation.")

    # 4) Walking vs cycling
    st.markdown("### Walking vs. cycling")
    mode = st.radio("Travel mode", ["Walking (stops within 500 m)", "Cycling (stops within 2 km)"], horizontal=True)
    col = "stops_500m" if mode.startswith("Walking") else "stops_2km"
    st.plotly_chart(px.scatter(plot_df, x=col, y="price_per_m2", opacity=0.3, trendline="ols",
                               labels={col: "Number of stops in reach", "price_per_m2": "€/m²"}), use_container_width=True)

    with st.expander("Technical limitations"):
        st.markdown(f"""
        * **Missing coordinates:** {n_missing_coords} of {n_raw} listings had no coordinates; the rest enter the analysis.
        * **Distance:** haversine on lat/lon. A degree of longitude is ~68 km at Amsterdam's latitude vs ~111 km for latitude, so subtracting degrees would distort distances by ~40%.
        * **Asking prices, one snapshot:** these are asking prices, not sale prices.
        * **Straight-line distance:** cyclists don't walk to the nearest stop. Hence the 2 km cycling metric.
        * **Association, not causation.**
        """)