# Why Do Patients Miss Clinic Appointments?

A SQL Server database and analysis of about 110,000 public clinic appointments from Vitória, Brazil, looking at what makes patients more likely to miss an appointment.

**Interactive dashboard:** https://ncollum.github.io/projects/clinic-no-shows/

## Key findings

- **Overall no-show rate: 20.2%** (22,314 of 110,516 appointments).
- **Wait time is the biggest factor.** 4.7% of same-day appointments are missed, compared with 33.0% of appointments booked more than 30 days ahead.
- **SMS reminders lower no-shows by about 6 to 7 percentage points** for appointments booked 8 or more days ahead (for example, 36.9% without an SMS vs 29.8% with one for 15 to 30 day waits). A simple overall comparison hides this, because reminders were mostly sent for long waits, which already have more no-shows.
- **The top 5 neighbourhoods account for 23.4% of all no-shows**, but the busiest neighbourhood has a below-average rate, so count and rate tell different stories.
- **Weekday barely matters** (19.4% to 21.2% from Monday to Friday).

## How it works

```
CSV (Kaggle)  ->  Python loader (Pandas, SQLAlchemy)  ->  SQL Server  ->  T-SQL views  ->  dashboard
                        |
                        +-> rows that fail checks go to load_rejects with the reason
```

**Database design** (`sql/02_create_tables.sql`)
- Normalized into `patients`, `neighbourhoods`, and `appointments` with primary and foreign keys.
- CHECK constraints for valid ages, handicap levels, and dates.
- A persisted computed column for the days between booking and appointment.

**Data loading and quality** (`python/load_data.py`)
- Validates every row and loads everything in one transaction.
- 11 rows failed checks and were logged in `load_rejects`: 5 patient IDs that were not whole numbers, 5 appointments dated before they were booked, and 1 negative age.

**Analysis** (`sql/03_views_and_procedures.sql`)
- Views for no-show rate by wait time, SMS reminder, age group, weekday, and neighbourhood.
- A Pareto view using window functions to find which neighbourhoods account for most no-shows.
- A stored procedure, `usp_no_show_summary`, that summarizes any date range or neighbourhood.

## Tech

SQL Server 2022 (Docker), T-SQL, Python, Pandas, SQLAlchemy, Plotly

## Run it yourself

1. Download `KaggleV2-May-2016.csv` from the [Medical Appointment No Shows dataset on Kaggle](https://www.kaggle.com/datasets/joniarroba/noshowappointments) into `data/raw/`.
2. Start SQL Server in Docker and put the SA password in a `.env` file as `DB_PASSWORD=...`.
3. Run the SQL scripts in order, then:
   ```
   pip install -r requirements.txt
   python python/load_data.py
   python python/build_web_data.py
   ```
