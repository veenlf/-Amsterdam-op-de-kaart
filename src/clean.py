import pandas as pd

def clean_funda(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(subset=["Street Address"])
    for c in ["Vraagprijs", "Wonen", "Latitude", "Longitude"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Wonen"])          # parking spots/garages without living area
    df["price_per_m2"] = df["Vraagprijs"] / df["Wonen"]
    df = df[df["Latitude"].between(52.2, 52.5) & df["Longitude"].between(4.6, 5.1)]
    return df