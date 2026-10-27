import pandas as pd

def price_stats(df: pd.DataFrame, price_col="Koopsom") -> pd.DataFrame:
    """Median/count/mean sale price per neighbourhood."""
    return (
        df.dropna(subset=["Buurt", price_col])
          .groupby("Buurt")[price_col]
          .agg(["count", "median", "mean"])
          .reset_index()
    )

def over_time(df: pd.DataFrame, price_col="Koopsom") -> pd.DataFrame:
    """Median sale price per year."""
    return (
        df.dropna(subset=["Datum overdracht", price_col])
          .assign(year=lambda d: d["Datum overdracht"].dt.year)
          .groupby("year")[price_col]
          .median()
          .reset_index()
    )