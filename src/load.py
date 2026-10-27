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
def load_fundM() -> pd.DataFrame:
    return pd.read_excel(
        RAW / "funda_M_samen_met_buurten_data_2026-10-03.xlsx",
        sheet_name="Sheet1",
        header=0,
    )

