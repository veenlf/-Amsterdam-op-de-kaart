import pandas as pd



def clean_kadaster(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Step 1: recover Koopsom values that are numbers followed by text.
    # e.g. "1200000 Kadastralegrootte 93 m²" -> "1200000"
    df["Koopsom"] = df["Koopsom"].astype(str).str.extract(r"(\d+\.?\d*)")[0]
    df["Koopsom"] = pd.to_numeric(df["Koopsom"], errors="coerce")

    # Step 2: drop rows with obviously broken coordinates
    # (real Amsterdam is roughly lat 52.2–52.5, lon 4.6–5.1)
    df = df[(df["Latitude"].between(52.2, 52.5)) & (df["Longitude"].between(4.6, 5.1))]

    # Step 3: add empty price_per_m2 column so we can join with Funda cleanly
    df["price_per_m2"] = float("nan")

    return df

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