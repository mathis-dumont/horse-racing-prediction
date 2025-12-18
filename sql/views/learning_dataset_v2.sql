CREATE OR REPLACE VIEW public.learning_dataset_v2 AS
WITH base AS (
  SELECT
    rp.participant_id,
    rp.race_id,
    r.meeting_id,
    rm.program_id,
    dp.program_date,

    r.race_number,
    r.distance_m,
    r.discipline,
    r.race_category,
    r.track_type,
    r.terrain_label,
    r.declared_runners_count,

    rm.meeting_number,
    rm.meeting_type,
    rm.racetrack_code,
    rm.weather_temperature,
    rm.weather_wind,

    rp.horse_id,
    h.sex AS horse_sex,
    h.birth_year,
    rp.age,
    rp.sex,
    rp.pmu_number,

    rp.shoeing_id,
    ls.code AS shoeing_code,
    rp.incident_id,
    li.code AS incident_code,

    rp.driver_jockey_id,
    rp.trainer_id,

    rp.career_races_count,
    rp.career_winnings,

    rp.finish_rank,
    (rp.finish_rank = 1)::int AS target_win,
    (rp.finish_rank <= 3)::int AS target_top3

  FROM public.race_participant rp
  JOIN public.race r
    ON r.race_id = rp.race_id
  JOIN public.race_meeting rm
    ON rm.meeting_id = r.meeting_id
  JOIN public.daily_program dp
    ON dp.program_id = rm.program_id
  LEFT JOIN public.horse h
    ON h.horse_id = rp.horse_id
  LEFT JOIN public.lookup_shoeing ls
    ON ls.shoeing_id = rp.shoeing_id
  LEFT JOIN public.lookup_incident li
    ON li.incident_id = rp.incident_id
  WHERE dp.program_date >= DATE '2023-01-01'
),

/* ===========================
   HISTO CHEVAL (avant course)
   =========================== */
horse_hist AS (
  SELECT
    b.participant_id,

    COUNT(*) FILTER (WHERE hrh.race_date < b.program_date) AS horse_hist_races,

    AVG((hrh.finish_rank = 1)::int)::float
      FILTER (WHERE hrh.race_date < b.program_date) AS horse_hist_win_rate,

    AVG((hrh.finish_rank <= 3)::int)::float
      FILTER (WHERE hrh.race_date < b.program_date) AS horse_hist_top3_rate,

    MAX(hrh.race_date)
      FILTER (WHERE hrh.race_date < b.program_date) AS horse_last_race_date

  FROM base b
  LEFT JOIN public.horse_race_history hrh
    ON hrh.horse_id = b.horse_id
  GROUP BY b.participant_id
),

/* ===================================
   HISTO JOCKEY / DRIVER (avant course)
   On utilise learning_dataset_v1 comme "historique"
   => garanti cohérent avec tes tables.
   =================================== */
jockey_hist AS (
  SELECT
    b.participant_id,

    COUNT(*) FILTER (WHERE v.program_date < b.program_date) AS jockey_hist_rides,

    AVG(v.target_win)::float
      FILTER (WHERE v.program_date < b.program_date) AS jockey_hist_win_rate,

    AVG(v.target_top3)::float
      FILTER (WHERE v.program_date < b.program_date) AS jockey_hist_top3_rate

  FROM base b
  LEFT JOIN public.learning_dataset_v1 v
    ON v.driver_jockey_id = b.driver_jockey_id
  GROUP BY b.participant_id
),

/* ==============================
   HISTO TRAINER (avant course)
   ============================== */
trainer_hist AS (
  SELECT
    b.participant_id,

    COUNT(*) FILTER (WHERE v.program_date < b.program_date) AS trainer_hist_starts,

    AVG(v.target_win)::float
      FILTER (WHERE v.program_date < b.program_date) AS trainer_hist_win_rate,

    AVG(v.target_top3)::float
      FILTER (WHERE v.program_date < b.program_date) AS trainer_hist_top3_rate

  FROM base b
  LEFT JOIN public.learning_dataset_v1 v
    ON v.trainer_id = b.trainer_id
  GROUP BY b.participant_id
)

SELECT
  b.*,

  -- Cheval
  hh.horse_hist_races,
  hh.horse_hist_win_rate,
  hh.horse_hist_top3_rate,
  (b.program_date - hh.horse_last_race_date) AS horse_days_since_last_race,

  -- Jockey/Driver
  jh.jockey_hist_rides,
  jh.jockey_hist_win_rate,
  jh.jockey_hist_top3_rate,

  -- Trainer
  th.trainer_hist_starts,
  th.trainer_hist_win_rate,
  th.trainer_hist_top3_rate

FROM base b
LEFT JOIN horse_hist hh
  ON hh.participant_id = b.participant_id
LEFT JOIN jockey_hist jh
  ON jh.participant_id = b.participant_id
LEFT JOIN trainer_hist th
  ON th.participant_id = b.participant_id;
