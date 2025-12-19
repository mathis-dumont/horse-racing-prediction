CREATE OR REPLACE VIEW v_raw_training_data AS
SELECT
    rp.participant_id,
    rp.race_id,
    rp.horse_id,
    dp.program_date,
    rm.meeting_number,
    r.race_number,
    r.discipline,
    r.distance_m,
    rm.racetrack_code,
    r.track_type,
    r.conditions_text,
    h.horse_name,
    h.birth_year,
    t.actor_name AS trainer_name,
    d.actor_name AS driver_name,
    ls.code AS shoeing_code,
    li.code AS incident_code,
    rp.age,
    rp.sex,
    rp.career_winnings,
    rp.pmu_number AS draw_number,
    rp.finish_rank,
    rp.live_odds,
    rp.time_achieved_s,
    rp.reduction_km,
    CASE 
        WHEN rp.finish_rank IS NOT NULL THEN 'FINISHED'
        WHEN li.code IS NOT NULL THEN li.code
        ELSE 'UNKNOWN'
    END AS finish_status
FROM race_participant rp
JOIN race r ON rp.race_id = r.race_id
JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
JOIN daily_program dp ON rm.program_id = dp.program_id
JOIN horse h ON rp.horse_id = h.horse_id
LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
LEFT JOIN racing_actor d ON rp.driver_jockey_id = d.actor_id
LEFT JOIN lookup_shoeing ls ON rp.shoeing_id = ls.shoeing_id
LEFT JOIN lookup_incident li ON rp.incident_id = li.incident_id;