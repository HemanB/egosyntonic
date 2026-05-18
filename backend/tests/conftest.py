"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force fixture mode + dev bypass before importing the app
os.environ.setdefault("EGOSYN_RUNTIME_MODE", "fixture")
os.environ.setdefault("EGOSYN_DEV_AUTH_BYPASS", "true")


@pytest.fixture
def client() -> TestClient:
    from reasoning.main import create_app

    return TestClient(create_app())
