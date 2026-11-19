SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

USE ClinicNoShow;
GO

DROP TABLE IF EXISTS dbo.appointments;
DROP TABLE IF EXISTS dbo.load_rejects;
DROP TABLE IF EXISTS dbo.patients;
DROP TABLE IF EXISTS dbo.neighbourhoods;
GO

CREATE TABLE dbo.neighbourhoods (
    neighbourhood_id   INT IDENTITY(1,1) CONSTRAINT pk_neighbourhoods PRIMARY KEY,
    neighbourhood_name NVARCHAR(100) NOT NULL CONSTRAINT uq_neighbourhood_name UNIQUE
);

CREATE TABLE dbo.patients (
    patient_id BIGINT NOT NULL CONSTRAINT pk_patients PRIMARY KEY,
    gender     CHAR(1) NOT NULL CONSTRAINT ck_patients_gender CHECK (gender IN ('F', 'M'))
);

CREATE TABLE dbo.appointments (
    appointment_id     INT NOT NULL CONSTRAINT pk_appointments PRIMARY KEY,
    patient_id         BIGINT NOT NULL CONSTRAINT fk_appt_patient REFERENCES dbo.patients (patient_id),
    neighbourhood_id   INT NOT NULL CONSTRAINT fk_appt_neighbourhood REFERENCES dbo.neighbourhoods (neighbourhood_id),
    scheduled_at       DATETIME2(0) NOT NULL,
    appointment_date   DATE NOT NULL,
    age_at_appointment TINYINT NOT NULL CONSTRAINT ck_appt_age CHECK (age_at_appointment BETWEEN 0 AND 120),
    scholarship        BIT NOT NULL,
    hypertension       BIT NOT NULL,
    diabetes           BIT NOT NULL,
    alcoholism         BIT NOT NULL,
    handicap_level     TINYINT NOT NULL CONSTRAINT ck_appt_handicap CHECK (handicap_level BETWEEN 0 AND 4),
    sms_received       BIT NOT NULL,
    no_show            BIT NOT NULL,
    wait_days AS DATEDIFF(DAY, CAST(scheduled_at AS DATE), appointment_date) PERSISTED,
    CONSTRAINT ck_appt_dates CHECK (appointment_date >= CAST(scheduled_at AS DATE))
);

CREATE INDEX ix_appt_patient ON dbo.appointments (patient_id);
CREATE INDEX ix_appt_date    ON dbo.appointments (appointment_date);

CREATE TABLE dbo.load_rejects (
    reject_id      INT IDENTITY(1,1) CONSTRAINT pk_load_rejects PRIMARY KEY,
    appointment_id BIGINT NULL,
    reason         NVARCHAR(200) NOT NULL,
    raw_row        NVARCHAR(MAX) NULL,
    rejected_at    DATETIME2(0) NOT NULL CONSTRAINT df_rejected_at DEFAULT SYSUTCDATETIME()
);
GO
