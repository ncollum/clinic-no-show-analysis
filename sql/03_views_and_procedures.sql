SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO
USE ClinicNoShow;
GO

-- One row per appointment with readable labels for analysis
CREATE OR ALTER VIEW dbo.vw_appointment_details AS
SELECT
    a.appointment_id,
    a.patient_id,
    p.gender,
    n.neighbourhood_name,
    a.scheduled_at,
    a.appointment_date,
    DATENAME(WEEKDAY, a.appointment_date) AS weekday_name,
    (DATEDIFF(DAY, '19000101', a.appointment_date) % 7) + 1 AS weekday_number,  -- Monday = 1
    a.wait_days,
    CASE WHEN a.wait_days = 0  THEN '0 days (same day)'
         WHEN a.wait_days <= 3 THEN '1-3 days'
         WHEN a.wait_days <= 7 THEN '4-7 days'
         WHEN a.wait_days <= 14 THEN '8-14 days'
         WHEN a.wait_days <= 30 THEN '15-30 days'
         ELSE '31+ days' END AS wait_group,
    CASE WHEN a.wait_days = 0  THEN 1
         WHEN a.wait_days <= 3 THEN 2
         WHEN a.wait_days <= 7 THEN 3
         WHEN a.wait_days <= 14 THEN 4
         WHEN a.wait_days <= 30 THEN 5
         ELSE 6 END AS wait_group_order,
    a.age_at_appointment,
    CASE WHEN a.age_at_appointment < 13 THEN '0-12'
         WHEN a.age_at_appointment < 18 THEN '13-17'
         WHEN a.age_at_appointment < 35 THEN '18-34'
         WHEN a.age_at_appointment < 55 THEN '35-54'
         WHEN a.age_at_appointment < 75 THEN '55-74'
         ELSE '75+' END AS age_group,
    a.scholarship, a.hypertension, a.diabetes, a.alcoholism, a.handicap_level,
    a.sms_received,
    a.no_show
FROM dbo.appointments AS a
JOIN dbo.patients AS p       ON p.patient_id = a.patient_id
JOIN dbo.neighbourhoods AS n ON n.neighbourhood_id = a.neighbourhood_id;
GO

CREATE OR ALTER VIEW dbo.vw_no_show_by_weekday AS
SELECT weekday_number, weekday_name,
       COUNT(*) AS appointments,
       SUM(CAST(no_show AS INT)) AS no_shows,
       CAST(100.0 * SUM(CAST(no_show AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS no_show_rate_pct
FROM dbo.vw_appointment_details
GROUP BY weekday_number, weekday_name;
GO

CREATE OR ALTER VIEW dbo.vw_no_show_by_wait_group AS
SELECT wait_group_order, wait_group,
       COUNT(*) AS appointments,
       SUM(CAST(no_show AS INT)) AS no_shows,
       CAST(100.0 * SUM(CAST(no_show AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS no_show_rate_pct
FROM dbo.vw_appointment_details
GROUP BY wait_group_order, wait_group;
GO

CREATE OR ALTER VIEW dbo.vw_no_show_by_age_group AS
SELECT age_group,
       COUNT(*) AS appointments,
       SUM(CAST(no_show AS INT)) AS no_shows,
       CAST(100.0 * SUM(CAST(no_show AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS no_show_rate_pct
FROM dbo.vw_appointment_details
GROUP BY age_group;
GO

-- SMS reminders compared within the same wait group, so the comparison is fair
CREATE OR ALTER VIEW dbo.vw_no_show_by_sms_and_wait AS
SELECT wait_group_order, wait_group, sms_received,
       COUNT(*) AS appointments,
       SUM(CAST(no_show AS INT)) AS no_shows,
       CAST(100.0 * SUM(CAST(no_show AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS no_show_rate_pct
FROM dbo.vw_appointment_details
GROUP BY wait_group_order, wait_group, sms_received;
GO

-- Pareto: which neighbourhoods account for most of the no-shows
CREATE OR ALTER VIEW dbo.vw_no_show_pareto_by_neighbourhood AS
WITH totals AS (
    SELECT neighbourhood_name,
           COUNT(*) AS appointments,
           SUM(CAST(no_show AS INT)) AS no_shows
    FROM dbo.vw_appointment_details
    GROUP BY neighbourhood_name
)
SELECT neighbourhood_name, appointments, no_shows,
       CAST(100.0 * no_shows / appointments AS DECIMAL(5,2)) AS no_show_rate_pct,
       CAST(100.0 * no_shows / SUM(no_shows) OVER () AS DECIMAL(5,2)) AS share_of_no_shows_pct,
       CAST(100.0 * SUM(no_shows) OVER (ORDER BY no_shows DESC, neighbourhood_name ROWS UNBOUNDED PRECEDING)
            / SUM(no_shows) OVER () AS DECIMAL(5,2)) AS cumulative_share_pct,
       RANK() OVER (ORDER BY no_shows DESC) AS no_show_rank
FROM totals;
GO

-- Patients who booked 3 or more times, with their no-show history
CREATE OR ALTER VIEW dbo.vw_repeat_patients AS
SELECT patient_id,
       COUNT(*) AS appointments,
       SUM(CAST(no_show AS INT)) AS no_shows,
       CAST(100.0 * SUM(CAST(no_show AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS no_show_rate_pct
FROM dbo.appointments
GROUP BY patient_id
HAVING COUNT(*) >= 3;
GO

CREATE OR ALTER VIEW dbo.vw_data_quality_summary AS
SELECT reason, COUNT(*) AS rejected_rows
FROM dbo.load_rejects
GROUP BY reason;
GO

-- Summary for a date range and, optionally, one neighbourhood
CREATE OR ALTER PROCEDURE dbo.usp_no_show_summary
    @start_date    DATE = NULL,
    @end_date      DATE = NULL,
    @neighbourhood NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT COUNT(*) AS appointments,
           SUM(CAST(no_show AS INT)) AS no_shows,
           CAST(100.0 * SUM(CAST(no_show AS INT)) / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS no_show_rate_pct
    FROM dbo.vw_appointment_details
    WHERE (@start_date IS NULL OR appointment_date >= @start_date)
      AND (@end_date IS NULL OR appointment_date <= @end_date)
      AND (@neighbourhood IS NULL OR neighbourhood_name = @neighbourhood);

    SELECT weekday_name,
           COUNT(*) AS appointments,
           CAST(100.0 * SUM(CAST(no_show AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS no_show_rate_pct
    FROM dbo.vw_appointment_details
    WHERE (@start_date IS NULL OR appointment_date >= @start_date)
      AND (@end_date IS NULL OR appointment_date <= @end_date)
      AND (@neighbourhood IS NULL OR neighbourhood_name = @neighbourhood)
    GROUP BY weekday_number, weekday_name
    ORDER BY weekday_number;
END;
GO
