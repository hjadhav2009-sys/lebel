from pathlib import Path


def test_initial_migration_is_explicit():
    migration = Path("alembic/versions/20260808_0001_catalog_foundation.py").read_text()
    assert "Base.metadata.create_all" not in migration
    assert "Base.metadata.drop_all" not in migration
    assert migration.count("op.create_table") >= 15
    assert "catalog_batches" in migration
    assert "print_agents" in migration
