# Supabase Migration Checklist (Milestone 1 / T1.2)

## Scope
- Execute `db/migrations/001_init.sql`
- Execute `db/migrations/002_add_client_request_id.sql`
- Create private Storage bucket `interview-audio`
- Configure Lifecycle Rule: delete objects older than 86400 seconds

## Verification SQL
```sql
SELECT typname FROM pg_type WHERE typname = 'question_type_enum';

SELECT COUNT(*)
FROM pg_policies
WHERE tablename IN ('questions', 'evaluations');

SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('questions', 'evaluations');

SELECT conname
FROM pg_constraint
WHERE conname = 'evaluations_client_request_id_unique';
```

## Expected
- `question_type_enum` exists
- policies count = 3
- `rowscurity` for both tables is `true`
- `evaluations_client_request_id_unique` exists
