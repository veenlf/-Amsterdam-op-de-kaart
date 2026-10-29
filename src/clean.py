import pandas as pd




def clean_funda(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(subset=["Street Address"])
    df["Vraagprijs"] = pd.to_numeric(df["Vraagprijs"], errors="coerce")
    df["Wonen"] = pd.to_numeric(df["Wonen"], errors="coerce")
    df["price_per_m2"] = df["Vraagprijs"] / df["Wonen"]
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df = df[(df["Latitude"].between(52.2, 52.5)) & (df["Longitude"].between(4.6, 5.1))]
            
    return df

def clean_cbs(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate CBS housing stock data to one row per year."""
    df = df.copy()
    
    # Extract 4-digit year: '2023JJ00' -> 2023
    df["year"] = pd.to_numeric(
        df["Perioden"].astype(str).str[:4], errors="coerce"
    )
    
    # Convert the stock column to numeric
    df["Voorraad"] = pd.to_numeric(
        df["BeginstandWoningvoorraad_1"], errors="coerce"
    )
    
    # Sum all house-type/class sub-categories per year
    result = (
        df.dropna(subset=["year", "Voorraad"])
          .groupby("year")["Voorraad"]
          .sum()
          .reset_index()
    )
    return result


import pandas as pd
from geopy.distance import geodesic

def calculate_stop_distances(fun_df, stops_df):
    # Drop houses without coordinates
    valid_houses = fun_df.dropna(subset=['Latitude', 'Longitude']).copy()
    
    # Function to find the closest stop for a single house
    def get_min_distance(lat, lon):
        # Create a tuple for the house
        house_loc = (lat, lon)
        # Calculate distance to ALL stops
        distances = stops_df.apply(
            lambda row: geodesic(house_loc, (row['lat'], row['lon'])).km, 
            axis=1
        )
        return distances.min()

    # Apply this to every house (This might take 10-20 seconds)
    valid_houses['dist_to_stop_km'] = valid_houses.apply(
        lambda row: get_min_distance(row['Latitude'], row['Longitude']), 
        axis=1
    )
    
    return valid_houses

# Also calculate distance to the center (Amsterdam Centraal)
def calculate_center_distance(fun_df):
    centraal = (52.379189, 4.899431)
    fun_df['dist_to_center_km'] = fun_df.apply(
        lambda row: geodesic(centraal, (row['Latitude'], row['Longitude'])).km 
        if pd.notna(row['Latitude']) else None, 
        axis=1
    )
    return fun_df