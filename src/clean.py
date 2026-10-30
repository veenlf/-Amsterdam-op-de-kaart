import pandas as pd

# Show full numbers everywhere: no scientific notation, no truncation.
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")   # 9166.67


def clean_funda(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(subset=["Street Address"])

    for c in ["Vraagprijs", "Wonen", "Latitude", "Longitude"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows that can't produce a meaningful price/m² (incl. "Onbekend")
    df = df.dropna(subset=["Vraagprijs", "Wonen"])
    df = df[df["Wonen"] > 0]                      # guard against /0

    # Standardise: whole euros per m², nullable Int64 (keeps <NA>, drops ".0")
    df["price_per_m2"] = (
        (df["Vraagprijs"] / df["Wonen"])
        .round(0)
        .astype("Int64")
    )

    df = df[
        df["Latitude"].between(52.2, 52.5)
        & df["Longitude"].between(4.6, 5.1)
    ]
    return df