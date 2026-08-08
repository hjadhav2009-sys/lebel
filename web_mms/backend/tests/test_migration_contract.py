from pathlib import Path


def test_initial_migration_is_explicit():
    migration = Path("alembic/versions/20260808_0001_catalog_foundation.py").read_text()
    assert "Base.metadata.create_all" not in migration
    assert "Base.metadata.drop_all" not in migration
    assert migration.count("op.create_table") >= 15
    assert "catalog_batches" in migration
    assert "print_agents" in migration


def test_phase2_migration_is_explicit_and_stacked():
    migration = Path("alembic/versions/20260809_0002_consignment_operations.py").read_text()
    assert 'down_revision = "20260808_0001"' in migration
    assert "Base.metadata.create_all" not in migration
    assert "consignment_issues" in migration
    assert "print_job_events" in migration
    assert "selected_for_print" in migration and "server_default=sa.false()" in migration
