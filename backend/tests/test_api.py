"""Basic API tests."""

import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app


client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "MyPoolr Circles API"
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    # May fail if database not configured, but endpoint should exist
    assert response.status_code in [200, 503]