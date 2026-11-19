"""Build the data file for the interactive dashboard on my website.

Groups every appointment by neighbourhood, age group, wait time, SMS reminder,
and weekday, so the web page can filter and recalculate rates instantly.

Run from the project folder:
    python python/build_web_data.py
"""
import json
from datetime import date
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

from load_data import ENV_PATH, PROJECT_DIR, read_env

OUT_PATH = PROJECT_DIR / "web" / "data.json"

CUBE_SQL = """
SELECT neighbourhood_name, age_group, wait_group_order, wait_group,
       CAST(sms_received AS INT) AS sms_received, weekday_number, weekday_name,
       COUNT(*) AS appointments,
       SUM(CAST(no_show AS INT)) AS no_shows
FROM dbo.vw_appointment_details
GROUP BY neighbourhood_name, age_group, wait_group_order, wait_group,
         sms_received, weekday_number, weekday_name
"""

AGE_GROUPS = ["0-12", "13-17", "18-34", "35-54", "55-74", "75+"]


def main():
    env = read_env(ENV_PATH)
    password = quote_plus(env["DB_PASSWORD"])
    engine = create_engine(f"mssql+pymssql://sa:{password}@localhost:1433/ClinicNoShow")

    cube = pd.read_sql(CUBE_SQL, engine)
    rejected = int(pd.read_sql("SELECT COUNT(*) AS n FROM dbo.load_rejects", engine)["n"][0])
    dates = pd.read_sql("SELECT MIN(appointment_date) AS first_day, MAX(appointment_date) AS last_day "
                        "FROM dbo.appointments", engine)

    neighbourhoods = sorted(cube["neighbourhood_name"].unique())
    wait_groups = (cube[["wait_group_order", "wait_group"]].drop_duplicates()
                   .sort_values("wait_group_order")["wait_group"].tolist())
    weekdays = (cube[["weekday_number", "weekday_name"]].drop_duplicates()
                .sort_values("weekday_number")["weekday_name"].tolist())

    # Store each row as small numbers (list positions) to keep the file light
    rows = [
        [neighbourhoods.index(r.neighbourhood_name), AGE_GROUPS.index(r.age_group),
         wait_groups.index(r.wait_group), int(r.sms_received), weekdays.index(r.weekday_name),
         int(r.appointments), int(r.no_shows)]
        for r in cube.itertuples()
    ]

    data = {
        "updated": date.today().isoformat(),
        "first_day": str(dates["first_day"][0]),
        "last_day": str(dates["last_day"][0]),
        "rejected_rows": rejected,
        "neighbourhoods": neighbourhoods,
        "age_groups": AGE_GROUPS,
        "wait_groups": wait_groups,
        "weekdays": weekdays,
        "columns": ["neighbourhood", "age_group", "wait_group", "sms", "weekday", "appointments", "no_shows"],
        "rows": rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {len(rows):,} groups to {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
