import pandas as pd

def build_key(street, num) -> str:
    if pd.isna(street) or pd.isna(num):
        return None
    street = str(street).strip().lower()
    num = str(num).strip().split()[0]   # "263 A" -> "263" (for Kadaster side, which is already clean)
    return f"{street}|{num}"

def split_funda_address(addr):
    """Return (street, number) from a Funda address string, or (None, None)."""
    if pd.isna(addr):
        return None, None
    m = pd.Series([str(addr)]).str.extract(r"^(.*?)\s+(\d+)\s*(.*)$")
    if m.iloc[0, 0] is None:
        return None, None
    return m.iloc[0, 0], m.iloc[0, 1]

def join_datasets(kad: pd.DataFrame, fun: pd.DataFrame) -> pd.DataFrame:
    kad = kad.copy()
    fun = fun.copy()

    # Kadaster side: street and number already separate
    kad["key"] = kad.apply(
        lambda r: build_key(r["Street Name"], r["Numeric"]),
        axis=1,
    )

    # Funda side: parse "Street 123 [suffix]" with regex
    parts = fun["Street Address"].astype(str).str.extract(r"^(.*?)\s+(\d+)\s*(.*)$")
    fun["_street"] = parts[0]
    fun["_number"] = parts[1]
    fun["key"] = fun.apply(lambda r: build_key(r["_street"], r["_number"]), axis=1)

    kad = kad.dropna(subset=["key"])
    fun = fun.dropna(subset=["key"])

    return kad.merge(fun, on="key", how="inner", suffixes=("_kad", "_funda"))