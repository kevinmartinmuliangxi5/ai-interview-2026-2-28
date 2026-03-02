-- Add idempotency key for weak-network retry deduplication.
ALTER TABLE evaluations
  ADD COLUMN IF NOT EXISTS client_request_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'evaluations_client_request_id_unique'
  ) THEN
    ALTER TABLE evaluations
      ADD CONSTRAINT evaluations_client_request_id_unique UNIQUE (client_request_id);
  END IF;
END
$$;

