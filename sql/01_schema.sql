-- =============================================================================
-- 01. SCHEMA DEFINITION (V4: OPTIMIZED & LIGHTWEIGHT)
-- Purpose: Horse Racing Data Warehouse
-- Strategy: High normalization for actors/lookups, optimized types (REAL/SMALLINT)
--           to minimize storage footprint on large historical datasets.
-- =============================================================================

-- Root entity representing a calendar day of racing events.
CREATE TABLE daily_program (
    program_id SERIAL PRIMARY KEY,
    program_date DATE UNIQUE
);

-- Represents a specific meeting (collection of races) at a racetrack.
-- Enforces uniqueness of meeting numbers within a single daily program.
CREATE TABLE race_meeting (
    meeting_id SERIAL PRIMARY KEY,
    program_id INT NOT NULL,
    meeting_number SMALLINT NOT NULL,
    meeting_type VARCHAR(30),
    racetrack_code VARCHAR(10),
    weather_temperature REAL,
    weather_wind VARCHAR(30),
    CONSTRAINT fk_program FOREIGN KEY (program_id) REFERENCES daily_program (program_id),
    CONSTRAINT uq_program_meeting_number UNIQUE (program_id, meeting_number)
);

-- Core entity defining the conditions and metadata of a specific race.
-- Data types are optimized (SMALLINT, REAL) for storage efficiency.
CREATE TABLE race (
    race_id SERIAL PRIMARY KEY,
    meeting_id INT NOT NULL,
    race_number SMALLINT NOT NULL,
    discipline VARCHAR(10),
    race_category VARCHAR(50),
    distance_m SMALLINT, -- 2 bytes: Sufficient for race distances (up to 32km).
    track_type VARCHAR(5),
    terrain_label VARCHAR(30),
    penetrometer REAL,   -- 4 bytes: Floating point precision sufficient for track readings.
    declared_runners_count SMALLINT,
    conditions_text TEXT, 
    race_status VARCHAR(10),
    race_duration_s INT,
    race_status_category VARCHAR(30), 
    CONSTRAINT fk_meeting FOREIGN KEY (meeting_id) REFERENCES race_meeting (meeting_id),
    CONSTRAINT uq_meeting_race_number UNIQUE (meeting_id, race_number)
);

-- Reference entity for Horses.
-- Acts as the central node for linking participants and history.
CREATE TABLE horse (
    horse_id SERIAL PRIMARY KEY,
    horse_name VARCHAR(100) NOT NULL,
    sex VARCHAR(1),
    birth_year SMALLINT,
    CONSTRAINT uq_horse_name UNIQUE (horse_name)
);

-- Reference entity for Humans (Jockeys, Drivers, Trainers).
CREATE TABLE racing_actor (
    actor_id SERIAL PRIMARY KEY,
    actor_name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_actor_name UNIQUE (actor_name)
);

-- Normalization table for Shoeing configurations (e.g., D4, PA, etc.).
CREATE TABLE lookup_shoeing (
    shoeing_id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE
);

-- Normalization table for Race Incidents (e.g., Galloping, Disqualified).
CREATE TABLE lookup_incident (
    incident_id SERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE
);

-- Join table: Links Horses, Races, and Actors.
-- Contains the specific performance metrics for a horse in a specific race.
CREATE TABLE race_participant (
    participant_id SERIAL PRIMARY KEY,
    race_id INT NOT NULL,
    horse_id INT NOT NULL,
    pmu_number SMALLINT NOT NULL,
    age SMALLINT,
    sex VARCHAR(1),
    trainer_id INT REFERENCES racing_actor (actor_id),
    driver_jockey_id INT REFERENCES racing_actor (actor_id),
    shoeing_id INT REFERENCES lookup_shoeing (shoeing_id),
    incident_id INT REFERENCES lookup_incident (incident_id),
    career_races_count SMALLINT,
    career_winnings REAL,    
    reference_odds REAL,
    live_odds REAL,
    raw_performance_string VARCHAR(255),
    finish_rank SMALLINT,
    time_achieved_s INT,
    reduction_km REAL,
    trainer_advice VARCHAR(30),
    CONSTRAINT fk_race FOREIGN KEY (race_id) REFERENCES race (race_id),
    CONSTRAINT fk_horse FOREIGN KEY (horse_id) REFERENCES horse (horse_id),
    CONSTRAINT uq_race_pmu_number UNIQUE (race_id, pmu_number)
);

-- Historical performance log for Horses.
-- Decoupled from the 'race' table to allow ingestion of past performance 
-- without requiring full race context/meeting data for those dates.
CREATE TABLE horse_race_history (
    history_id SERIAL PRIMARY KEY,
    horse_id INT NOT NULL,
    race_date DATE,
    discipline VARCHAR(20),
    prize_money REAL,
    distance_m SMALLINT,
    first_place_time_s INT,
    finish_place SMALLINT,
    finish_status VARCHAR(20),
    jockey_weight REAL,
    draw_number SMALLINT,
    reduction_km REAL,
    distance_traveled_m SMALLINT,
    CONSTRAINT fk_horse_history FOREIGN KEY (horse_id) REFERENCES horse (horse_id),
    CONSTRAINT uq_horse_history UNIQUE (horse_id, race_date, discipline, distance_m)
);

-- Betting Metadata: Defines the type of bets available for a race.
CREATE TABLE race_bet (
    bet_id SERIAL PRIMARY KEY,
    race_id INT NOT NULL,
    bet_type VARCHAR(10),
    bet_family VARCHAR(20),
    base_stake REAL,
    is_refunded BOOLEAN,
    CONSTRAINT fk_race_bet FOREIGN KEY (race_id) REFERENCES race (race_id),
    CONSTRAINT uq_race_bet UNIQUE (race_id, bet_type)
);

-- Betting Outcomes: Stores dividends and winning combinations.
-- One-to-Many relationship with race_bet.
CREATE TABLE bet_report (
    report_id SERIAL PRIMARY KEY,
    bet_id INT NOT NULL,
    combination VARCHAR(50),
    dividend REAL,           
    dividend_per_1e REAL,
    winners_count REAL, 
    CONSTRAINT fk_bet_report FOREIGN KEY (bet_id) REFERENCES race_bet (bet_id),
    CONSTRAINT uq_bet_report UNIQUE (bet_id, combination)
);

-- ML Inference Storage.
-- Stores probabilities generated by predictive models, linked to specific participants.
CREATE TABLE prediction (
    prediction_id SERIAL PRIMARY KEY,
    participant_id INT NOT NULL,
    model_version VARCHAR(20),
    proba_winner REAL,
    proba_top3_place REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_participant_prediction FOREIGN KEY (participant_id) REFERENCES race_participant (participant_id)
);