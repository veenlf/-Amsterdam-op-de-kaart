from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
#  absolute path to the raw data folder^ this makes it easier to load the data from anywhere in the project

#  for loading extra data, we use the pandas read_excel function to read the excel file and return a dataframe
def load_kadaster() -> pd.DataFrame:
    df = pd.read_csv(RAW / "clean_kadaster_data.csv")
    df["Datum overdracht"] = pd.to_datetime(df["Datum overdracht"], errors="coerce")
    return df 

#  for loading thefundM data, we use the pandas read_excel function to read the excel file and return a dataframe
def load_funda() -> pd.DataFrame:
    candidates = list(RAW.glob("funda_M_*.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No funda_M_*.xlsx found in {RAW}")
    
    # Picks the newest file if there are multiple
    path = sorted(candidates)[-1] 
    
    return pd.read_excel(
        path,
        sheet_name="Sheet1",
        header=0,
    )