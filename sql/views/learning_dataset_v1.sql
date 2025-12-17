CREATE OR REPLACE VIEW public.learning_dataset_v1 AS
SELECT
  -- Identifiants
  rp.participant_id,
  rp.race_id,
  r.meeting_id,
  rm.program_id,
  dp.program_date,

  -- Course
  r.race_number,
  r.distance_m,
  r.discipline,
  r.race_category,
  r.track_type,
  r.terrain_label,
  r.declared_runners_count,

  -- Meeting (météo etc.)
  rm.meeting_number,
  rm.meeting_type,
  rm.racetrack_code,
  rm.weather_temperature,
  rm.weather_wind,

  -- Participant / cheval
  rp.horse_id,
  h.horse_sex,
  h.birth_year,
  rp.age,
  rp.sex,
  rp.pmu_number,
  rp.shoeing_id,
  ls.code AS shoeing_code,
  rp.incident_id,
  li.code AS incident_code,

  -- Acteurs
  rp.driver_jockey_id,
  dj.actor_name AS driver_jockey_name,
  rp.trainer_id,
  tr.actor_name AS trainer_name,

  -- Stats ingestion
  rp.career_races_count,
  rp.career_winnings,

  -- Targets
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
LEFT JOIN public.racing_actor dj
  ON dj.actor_id = rp.driver_jockey_id
LEFT JOIN public.racing_actor tr
  ON tr.actor_id = rp.trainer_id
WHERE dp.program_date >= DATE '2023-01-01';
