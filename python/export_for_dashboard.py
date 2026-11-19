"""Export the analysis views from SQL Server to CSV files for the Tableau dashboard.

Run from the project folder:
    python python/export_for_dashboard.py
"""
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

from load_data import ENV_PATH, PROJECT_DIR, read_env

OUT_DIR = PROJECT_DIR / "data" / "processed"

VIEWS = [
    "vw_appointment_details",
    "vw_no_show_by_weekday",
    "vw_no_show_by_wait_group",
    "vw_no_show_by_age_group",
    "vw_no_show_by_sms_and_wait",
    "vw_no_show_pareto_by_neighbourhood",
    "vw_data_quality_summary",
]


def main():
    env = read_env(ENV_PATH)
    password = quote_plus(env["DB_PASSWORD"])
    engine = create_engine(f"mssql+pymssql://sa:{password}@localhost:1433/ClinicNoShow")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for view in VIEWS:
        df = pd.read_sql(f"SELECT * FROM dbo.{view}", engine)
        name = view.removeprefix("vw_")
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"{name}.csv: {len(df):,} rows")
    print(f"Saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
