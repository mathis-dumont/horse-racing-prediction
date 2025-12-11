-- Migration 02: Add unique constraints for idempotent ingestion
-- Minimal required constraints for upserting data reliably

------------------------------------------------------------
-- 1) horse : required for UPSERT in ingest_participants
------------------------------------------------------------
ALTER TABLE horse
ADD CONSTRAINT uq_horse_name UNIQUE (horse_name);


------------------------------------------------------------
-- 2) horse_race_history : required to avoid duplicate past performances
------------------------------------------------------------
ALTER TABLE horse_race_history
ADD CONSTRAINT uq_horse_history UNIQUE (horse_id, race_date, discipline, distance_m);


------------------------------------------------------------
-- 3) race_bet : each bet type appears once per race
------------------------------------------------------------
ALTER TABLE race_bet
ADD CONSTRAINT uq_race_bet UNIQUE (race_id, bet_type);


------------------------------------------------------------
-- 4) bet_report : each combination appears once per bet
------------------------------------------------------------
ALTER TABLE bet_report
ADD CONSTRAINT uq_bet_report UNIQUE (bet_id, combination);
