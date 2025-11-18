-- DBeaver / PostgreSQL SQL Script

-- Table 1: daily_program
CREATE TABLE daily_program (
    program_id SERIAL PRIMARY KEY, -- PK, auto-increment
    program_date DATE UNIQUE       -- Constraint: program_date unique
);

-- Table 2: race_meeting
CREATE TABLE race_meeting (
    meeting_id SERIAL PRIMARY KEY, -- PK, using SERIAL for auto-increment as id_reunion was not explicitely auto-increment
    program_id INT NOT NULL,       -- FK -> daily_program
    meeting_number INT NOT NULL,
    meeting_type TEXT,
    racetrack_code TEXT,
    weather_temperature NUMERIC,
    weather_wind TEXT,
    CONSTRAINT fk_program
        FOREIGN KEY (program_id)
        REFERENCES daily_program (program_id),
    CONSTRAINT uq_program_meeting_number UNIQUE (program_id, meeting_number) -- Constraint: (program_id, meeting_number) unique
);

-- Table 3: race
CREATE TABLE race (
    race_id SERIAL PRIMARY KEY,      -- PK, using SERIAL for auto-increment
    meeting_id INT NOT NULL,         -- FK -> race_meeting
    race_number INT NOT NULL,
    discipline TEXT,
    race_category TEXT,
    age_condition TEXT,
    distance_m INT,
    track_type TEXT,
    terrain_label TEXT,
    penetrometer NUMERIC,
    declared_runners_count INT,
    conditions_text TEXT,
    race_status TEXT,
    finish_order_raw JSONB,         -- Stores raw finish order as JSONB
    race_duration_s INT,             -- Duration in seconds
    race_status_category TEXT,
    CONSTRAINT fk_meeting
        FOREIGN KEY (meeting_id)
        REFERENCES race_meeting (meeting_id),
    CONSTRAINT uq_meeting_race_number UNIQUE (meeting_id, race_number) -- Constraint: (meeting_id, race_number) unique
);

-- Table 4: horse
CREATE TABLE horse (
    horse_id SERIAL PRIMARY KEY, -- PK, auto-increment
    horse_name TEXT NOT NULL,
    sex TEXT,
    birth_year INT              -- Nullable
);

-- Table 5: race_participant
-- Central table for race participants
CREATE TABLE race_participant (
    participant_id SERIAL PRIMARY KEY, -- PK, auto-increment
    race_id INT NOT NULL,             -- FK -> race
    horse_id INT NOT NULL,            -- FK -> horse
    pmu_number INT NOT NULL,
    age INT,
    sex TEXT,
    trainer_name TEXT,
    driver_jockey_name TEXT,
    shoeing_status TEXT,              -- Deferrage
    career_races_count INT,
    career_winnings NUMERIC,
    reference_odds NUMERIC,
    live_odds NUMERIC,
    raw_performance_string TEXT,      -- Musique brute
    
    -- Targets (post-race)
    finish_rank INT,
    incident TEXT,
    time_achieved_s INT,              -- Time in seconds
    reduction_km NUMERIC,             -- Reduction_km
    post_race_comment TEXT,
    trainer_advice TEXT,
    
    CONSTRAINT fk_race
        FOREIGN KEY (race_id)
        REFERENCES race (race_id),
    CONSTRAINT fk_horse
        FOREIGN KEY (horse_id)
        REFERENCES horse (horse_id),
    CONSTRAINT uq_race_pmu_number UNIQUE (race_id, pmu_number) -- Constraint: (race_id, pmu_number) unique
);

-- Table 6: horse_race_history
CREATE TABLE horse_race_history (
    history_id SERIAL PRIMARY KEY, -- PK, auto-increment
    horse_id INT NOT NULL,         -- FK -> horse
    race_date DATE,
    discipline TEXT,
    prize_money NUMERIC,           -- Allocation
    distance_m INT,
    first_place_time_s INT,        -- Temps premier en secondes
    finish_place INT,
    finish_status TEXT,
    jockey_weight NUMERIC,
    draw_number INT,               -- Corde (position de départ)
    reduction_km NUMERIC,
    distance_traveled_m INT,       -- Distance parcourue en mètres
    CONSTRAINT fk_horse_history
        FOREIGN KEY (horse_id)
        REFERENCES horse (horse_id)
);

-- Table 7: race_bet
CREATE TABLE race_bet (
    bet_id SERIAL PRIMARY KEY, -- PK, auto-increment
    race_id INT NOT NULL,      -- FK -> race
    bet_type TEXT,
    bet_family TEXT,
    base_stake NUMERIC,        -- Mise de base
    is_refunded BOOLEAN,
    CONSTRAINT fk_race_bet
        FOREIGN KEY (race_id)
        REFERENCES race (race_id)
);

-- Table 8: bet_report
CREATE TABLE bet_report (
    report_id SERIAL PRIMARY KEY,  -- PK, auto-increment
    bet_id INT NOT NULL,           -- FK -> race_bet
    combination TEXT,
    dividend NUMERIC,
    dividend_per_1e NUMERIC,       -- Dividende pour 1€
    winners_count NUMERIC,         -- Nb gagnants
    CONSTRAINT fk_bet_report
        FOREIGN KEY (bet_id)
        REFERENCES race_bet (bet_id)
);

-- Table 9: prediction
CREATE TABLE prediction (
    prediction_id SERIAL PRIMARY KEY,     -- PK, auto-increment
    participant_id INT NOT NULL,          -- FK -> race_participant
    model_version TEXT,
    proba_winner NUMERIC,                 -- Probability of winning
    proba_top3_place NUMERIC,             -- Probability of placing in top 3
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Timestamp of creation
    CONSTRAINT fk_participant_prediction
        FOREIGN KEY (participant_id)
        REFERENCES race_participant (participant_id)
);

-- (OPTIONAL) Table 10: Raw JSON tables
CREATE TABLE raw_program_data (
    id SERIAL PRIMARY KEY,
    program_date DATE,
    payload_json JSONB
);

CREATE TABLE raw_participants_data (
    id SERIAL PRIMARY KEY,
    program_date DATE,
    payload_json JSONB
);

CREATE TABLE raw_performances_data (
    id SERIAL PRIMARY KEY,
    program_date DATE,
    payload_json JSONB
);

CREATE TABLE raw_reports_data (
    id SERIAL PRIMARY KEY,
    program_date DATE,
    payload_json JSONB
);