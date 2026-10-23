import shutil

import pytest

from app.config import Settings
from app.core.errors import ApiError
from app.core.sessions import SessionStore


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def store(tmp_path):
    clock = Clock()
    s = SessionStore(Settings(storage_dir=tmp_path, session_ttl_seconds=100, max_sessions=2), clock)
    s.clock = clock
    return s


def test_ids_random_and_token_required(store):
    a, ta = store.create()
    b, tb = store.create()
    assert a.session_id != b.session_id and ta != tb
    assert store.authenticate(a.session_id, ta) is a
    for bad in (None, "", tb, "x"):
        with pytest.raises(ApiError) as e:
            store.authenticate(a.session_id, bad)
        assert e.value.status == 404
    with pytest.raises(ApiError):
        store.authenticate("nope", ta)


def test_expiry_is_fixed_from_creation_and_deletes_files(store):
    s, tok = store.create()
    p = store.source_path(s.session_id, "abc", 1)
    p.write_bytes(b"x")
    store.clock.t += 99
    store.authenticate(s.session_id, tok)  # chưa hết hạn, và truy cập KHÔNG gia hạn
    store.clock.t += 2
    with pytest.raises(ApiError):
        store.authenticate(s.session_id, tok)
    assert not p.exists()


def test_cleanup_failure_freezes_session_and_is_retried(store, monkeypatch):
    s, tok = store.create()
    p = store.source_path(s.session_id, "abc", 1)
    p.write_bytes(b"x")
    real = shutil.rmtree
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    result = store.delete(s)
    assert result.deleted is False and result.cleanup_error == "CLEANUP_FAILED"
    with pytest.raises(ApiError):  # bị đóng băng: không truy cập được nữa
        store.authenticate(s.session_id, tok)
    assert store.purge_expired() == (0, 1)
    monkeypatch.setattr(shutil, "rmtree", real)
    assert store.purge_expired() == (1, 0)
    assert not p.exists()


def test_max_sessions(store):
    store.create(); store.create()
    with pytest.raises(ApiError) as e:
        store.create()
    assert e.value.status == 429


def test_wipe_all_only_touches_session_dirs(store, tmp_path):
    s, _ = store.create()
    store.source_path(s.session_id, "a", 1).write_bytes(b"x")
    keep = tmp_path / "keep.txt"
    keep.write_text("do not delete")
    store.wipe_all()
    assert keep.exists() and not any(c.name.startswith("sess_") for c in tmp_path.iterdir())
