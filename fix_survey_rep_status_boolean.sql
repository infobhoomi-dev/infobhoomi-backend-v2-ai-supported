-- ============================================================================
-- Fix: survey_rep.status is character varying but the Django model declares it
-- as BooleanField. This makes filter(status=True) generate SQL that Postgres
-- rejects ("argument of AND must be type boolean, not type character varying"),
-- which 500s the query builder (/api/user/query-parcels/) and any other view
-- that filters survey_rep on status.
--
-- The column holds the strings 'true' / 'false', which cast cleanly to boolean.
-- This aligns the local DB with the model (and with the hosted schema).
--
-- Safe to run once. Take a DB backup first if this is precious data.
-- ============================================================================

BEGIN;

ALTER TABLE survey_rep ALTER COLUMN status DROP DEFAULT;
ALTER TABLE survey_rep ALTER COLUMN status TYPE boolean USING (status::boolean);
ALTER TABLE survey_rep ALTER COLUMN status SET DEFAULT false;

COMMIT;

-- Verify:
-- SELECT data_type, column_default FROM information_schema.columns
--   WHERE table_name='survey_rep' AND column_name='status';   -- expect: boolean, false
-- SELECT status, count(*) FROM survey_rep GROUP BY status;     -- expect: t / f
