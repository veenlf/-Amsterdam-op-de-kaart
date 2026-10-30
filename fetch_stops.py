import requests
import pandas as pd
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

def fetch_stops():
    print("Fetching stops from OpenStreetMap...")
    # Use HTTPS instead of HTTP
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    overpass_query = """
    [out:json][timeout:60];
    (
    node["railway"="tram_stop"](52.2,4.6,52.5,5.1);
    node["railway"="station"]["station"="subway"](52.2,4.6,52.5,5.1);
    );
    out;
    """
    
    # 1. Add a proper User-Agent header (this fixes the 406 error)
    # 2. Send the query as POST data, not as URL parameters
    headers = {
        'User-Agent': 'AmsterdamHousingDashboard/1.0 (student project)',
        'Accept': 'application/json',
    }
    
    response = requests.post(
        overpass_url, 
        data={'data': overpass_query}, 
        headers=headers, 
        timeout=60
    )
    
    print(f"Status: {response.status_code}")
    response.raise_for_status()  # This will now pass if the query is correct
    data = response.json()

    stops = []
    for element in data['elements']:
        if 'lat' in element and 'lon' in element:
            stops.append({
                'name': element.get('tags', {}).get('name', 'Unknown'),
                'lat': element['lat'],
                'lon': element['lon'],
                'type': 'metro' if element.get('tags', {}).get('station') == 'subway' else 'tram',
            })

    df = pd.DataFrame(stops)
    df = df.drop_duplicates(subset=['lat', 'lon'])
    print(df['type'].value_counts())
    out_file = RAW / "tram_stops.csv"
    df.to_csv(out_file, index=False)
    print(f"Successfully saved {len(df)} stops to {out_file}")

if __name__ == "__main__":
    fetch_stops()