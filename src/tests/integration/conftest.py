import pytest
from fastapi.testclient import TestClient
from presentation.api.main import app   # ← points to clean main

@pytest.fixture(scope="session")
def client():
    return TestClient(app)