import requests
import pandas as pd
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"
BASE = "https://opendata.cbs.nl/ODataApi/OData/83704NED"

def fetch_amsterdam():
    # Use UntypedDataSet, which handles filters better than Observations
    url = f"{BASE}/UntypedDataSet"
    
    # CBS requires the filter value in single quotes, and the column is RegioS
    params = {
        "$filter": "RegioS eq 'GM0363'",
        "$top": 10000,  # Should be enough for one municipality
    }
    
    r = requests.get(url, params=params, timeout=60)
    print('Status:', r.status_code)
    
    if r.status_code != 200:
        print('Response:', r.text[:500])
        r.raise_for_status()
        
    data = r.json()["value"]
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    df = fetch_amsterdam()
    out = RAW / "cbs_woningvoorraad_amsterdam.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows.")
    print("Columns:", df.columns.tolist())
    print(df.head(3).to_string())