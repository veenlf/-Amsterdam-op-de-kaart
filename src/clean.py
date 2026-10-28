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
    return df