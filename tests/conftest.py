import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Las pruebas nunca llaman a la IA real.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "pruebas",
        "DATABASE": str(tmp_path / "test.db"),
    })


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, email="ana@example.com", password="secreta123", nombre="Ana"):
    return client.post("/api/auth/register", json={
        "nombre": nombre, "email": email, "password": password,
    })


@pytest.fixture
def logged_client(client):
    assert register(client).status_code == 201
    return client
