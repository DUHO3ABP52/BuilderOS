import os
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "_runtime_test.db"
if _DB_PATH.exists():
    _DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["FIRST_USER_EMAIL"] = "admin@example.com"
os.environ["FIRST_USER_PASSWORD"] = "change-me"
os.environ["APP_ENV"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["LLM_ENABLED"] = "false"
os.environ["RAG_ENABLED"] = "true"
os.environ["EMBEDDING_BASE_URL"] = "http://127.0.0.1:9"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "change-me"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
