"""Load the Kaggle medical appointment no-show CSV into SQL Server.

Steps:
1. Read the raw CSV.
2. Clean it and split out rows that break the rules (kept in load_rejects).
3. Load neighbourhoods, patients, and appointments into their own tables.

Run from the project folder:
    python python/load_data.py
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_DIR / "data" / "raw" / "KaggleV2-May-2016.csv"
ENV_PATH = PROJECT_DIR / ".env"


def read_env(path):
    """Read KEY=VALUE lines from the .env file."""
    values = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def to_whole_number(value):
    """Return the value as an int, or None if it is not a whole number."""
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    if number != number.to_integral_value():
        return None
    return int(number)


def clean(raw):
    """Return (good_rows, rejected_rows) as two DataFrames."""
    df = raw.rename(columns={
        "PatientId": "patient_id_raw",
        "AppointmentID": "appointment_id",
        "Gender": "gender",
        "ScheduledDay": "scheduled_raw",
        "AppointmentDay": "appointment_raw",
        "Age": "age_at_appointment",
        "Neighbourhood": "neighbourhood_name",
        "Scholarship": "scholarship",
        "Hipertension": "hypertension",   # fix spelling from the source
        "Diabetes": "diabetes",
        "Alcoholism": "alcoholism",
        "Handcap": "handicap_level",       # fix spelling from the source
        "SMS_received": "sms_received",
        "No-show": "no_show_raw",
    })

    df["patient_id"] = df["patient_id_raw"].map(to_whole_number)
    df["scheduled_at"] = pd.to_datetime(df["scheduled_raw"], utc=True).dt.tz_localize(None)
    df["appointment_date"] = pd.to_datetime(df["appointment_raw"], utc=True).dt.tz_localize(None).dt.normalize()
    df["no_show"] = (df["no_show_raw"].str.strip().str.lower() == "yes").astype(int)
    df["neighbourhood_name"] = df["neighbourhood_name"].str.strip()

    # Each rule: (reason shown in load_rejects, rows that break it)
    rules = [
        ("PatientId is not a whole number", df["patient_id"].isna()),
        ("Age outside 0 to 120", ~df["age_at_appointment"].between(0, 120)),
        ("Appointment date is before the booking date",
         df["appointment_date"] < df["scheduled_at"].dt.normalize()),
        ("Handicap level outside 0 to 4", ~df["handicap_level"].between(0, 4)),
        ("Gender is not F or M", ~df["gender"].isin(["F", "M"])),
        ("Duplicate AppointmentID", df["appointment_id"].duplicated(keep="first")),
    ]

    reasons = pd.Series("", index=df.index)
    for reason, broken in rules:
        reasons = reasons.where(~broken, reasons.where(reasons == "", reasons + "; ") + reason)
    bad_mask = reasons != ""

    rejects = pd.DataFrame({
        "appointment_id": df.loc[bad_mask, "appointment_id"],
        "reason": reasons[bad_mask],
        "raw_row": raw.loc[bad_mask].astype(str).agg(",".join, axis=1),
    })
    good = df.loc[~bad_mask].copy()
    good["patient_id"] = good["patient_id"].astype("int64")
    good["appointment_date"] = good["appointment_date"].dt.date
    return good, rejects


def load(engine, good, rejects):
    """Replace the table contents with the cleaned data, all in one transaction."""
    with engine.begin() as conn:
        for table in ["appointments", "load_rejects", "patients", "neighbourhoods"]:
            conn.execute(text(f"DELETE FROM dbo.{table}"))

        def insert(df, table):
            # SQL Server allows about 2,100 parameters per statement
            rows_per_batch = max(1, 2000 // len(df.columns))
            df.to_sql(table, conn, schema="dbo", if_exists="append", index=False,
                      method="multi", chunksize=rows_per_batch)

        neighbourhoods = pd.DataFrame(
            {"neighbourhood_name": sorted(good["neighbourhood_name"].unique())})
        insert(neighbourhoods, "neighbourhoods")
        ids = pd.read_sql("SELECT neighbourhood_id, neighbourhood_name FROM dbo.neighbourhoods", conn)
        good = good.merge(ids, on="neighbourhood_name", how="left")

        # One row per patient. If a patient has more than one gender value, keep the first one.
        patients = good.sort_values("scheduled_at").drop_duplicates("patient_id")[["patient_id", "gender"]]
        insert(patients, "patients")

        appointment_columns = [
            "appointment_id", "patient_id", "neighbourhood_id", "scheduled_at", "appointment_date",
            "age_at_appointment", "scholarship", "hypertension", "diabetes", "alcoholism",
            "handicap_level", "sms_received", "no_show",
        ]
        insert(good[appointment_columns], "appointments")
        if len(rejects):
            insert(rejects, "load_rejects")

        counts = {
            table: conn.execute(text(f"SELECT COUNT(*) FROM dbo.{table}")).scalar()
            for table in ["neighbourhoods", "patients", "appointments", "load_rejects"]
        }
    return counts


def main():
    env = read_env(ENV_PATH)
    password = quote_plus(env["DB_PASSWORD"])
    engine = create_engine(f"mssql+pymssql://sa:{password}@localhost:1433/ClinicNoShow")

    raw = pd.read_csv(CSV_PATH, dtype={"PatientId": str})
    print(f"Read {len(raw):,} rows from {CSV_PATH.name}")

    good, rejects = clean(raw)
    print(f"Clean rows: {len(good):,}   Rejected rows: {len(rejects):,}")
    for reason, count in rejects["reason"].value_counts().items():
        print(f"  - {reason}: {count}")

    print("Loading into SQL Server...")
    counts = load(engine, good, rejects)
    for table, count in counts.items():
        print(f"  {table}: {count:,} rows")
    print("Done.")


if __name__ == "__main__":
    main()
