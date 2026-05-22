import pytest


@pytest.fixture(autouse=True)
async def temp_storage(monkeypatch, tmp_path):
    """Each test gets a fresh SQLite file and a clean cached connection."""
    monkeypatch.setenv("SIMAB_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SIMAB_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

    # Reset cached config
    from simab import config as cfg
    cfg.CONFIG = cfg.Config.from_env()

    # Close any cached DB connection from a previous test
    from simab import state
    if state._db is not None:
        try:
            await state._db.close()
        except Exception:
            pass
        state._db = None

    yield

    # Cleanup after test
    if state._db is not None:
        try:
            await state._db.close()
        except Exception:
            pass
        state._db = None
