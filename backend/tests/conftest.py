from __future__ import annotations

import dataclasses
import io

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"x" * 64


@pytest.fixture
def settings(tmp_path):
    return Settings(storage_dir=tmp_path / "data", max_upload_bytes=1024 * 1024, analyze_timeout_seconds=2.0)


@pytest.fixture
def make_client(settings):
    clients = []

    def _make(**overrides):
        app = create_app(dataclasses.replace(settings, **overrides.pop("settings", {})), **overrides)
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


class Sess:
    """Helper: một session đã tạo sẵn + header token."""

    def __init__(self, client: TestClient):
        self.c = client
        body = client.post("/api/v1/sessions").json()
        self.id = body["session_id"]
        self.h = {"X-Session-Token": body["access_token"]}
        self.base = f"/api/v1/sessions/{self.id}"

    def upload(self, data: bytes, name: str, mime: str = "application/octet-stream"):
        return self.c.post(f"{self.base}/sources", headers=self.h, files={"file": (name, io.BytesIO(data), mime)})

    def analyze(self, **body):
        return self.c.post(f"{self.base}/analyze", headers=self.h, json=body)


@pytest.fixture
def sess(client):
    return Sess(client)
