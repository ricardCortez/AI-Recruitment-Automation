"""
Tests de autenticación — verifica login, token y roles.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_invalido():
    r = client.post("/api/v1/auth/login", json={"username": "noexiste", "password": "mal"})
    assert r.status_code == 401


def test_login_admin():
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@2025!"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["rol"] == "admin"


def test_endpoint_protegido_sin_token():
    r = client.get("/api/v1/users/")
    assert r.status_code == 403  # Sin token → sin acceso
