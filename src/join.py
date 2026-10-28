import pandas as pd

def build_key(street, num) -> str:
    if pd.isna(street) or pd.isna(num):
        return None
    street = str(street).strip().lower()
    # Strip suffixes: "86-B" -> "86", "86 B" -> "86", "86" -> "86"
    num = str(num).strip().split()[0] 
    # Also handle hyphens just in case (e.g., "86-B" -> "86")
    num = num.split("-")[0]
    return f"{street}|{num}"

def join_datasets(kad: pd.DataFrame, fun: pd.DataFrame) -> pd.DataFrame:
    kad = kad.copy()
    fun = fun.copy()

    # Kadaster: street and number are already separate columns
    kad["key"] = kad.apply(
        lambda r: build_key(r["Street Name"], r["Numeric"]),
        axis=1,
    )

    # Funda: parse "Street Address" like "Transvaalkade 86-B" using regex
    # This matches: (any characters) + (space) + (digits) + (anything else)
    parts = fun["Street Address"].astype(str).str.extract(r"^(.*?)\s+(\d+)\s*(.*)$")
    fun["_street"] = parts[0]
    fun["_number"] = parts[1]
    
    # Build the key for Funda
    fun["key"] = fun.apply(lambda r: build_key(r["_street"], r["_number"]), axis=1)

    # Drop rows where we couldn't build a key (else None matches None!)
    kad = kad.dropna(subset=["key"])
    fun = fun.dropna(subset=["key"])

    return kad.merge(fun, on="key", how="inner", suffixes=("_kad", "_funda"))