from pathlib import Path


def test_supabase_migration_files_exist() -> None:
    root = Path(__file__).resolve().parents[3]
    m1 = root / 'db' / 'migrations' / '001_init.sql'
    m2 = root / 'db' / 'migrations' / '002_add_client_request_id.sql'
    assert m1.exists(), '001_init.sql must exist'
    assert m2.exists(), '002_add_client_request_id.sql must exist'


def test_idempotency_column_migration_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    m2 = (root / 'db' / 'migrations' / '002_add_client_request_id.sql').read_text(
        encoding='utf-8', errors='ignore'
    )
    assert 'client_request_id' in m2
    assert 'UNIQUE' in m2.upper()
