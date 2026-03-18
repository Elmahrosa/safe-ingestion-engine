# tests/conftest.py
from __future__ import annotations
import os
import pytest
from unittest.mock import patch
from core.config import Settings

@pytest.fixture(autouse=True)
def mock_settings_for_tests():
    """Override Settings with test-safe defaults for all tests."""
    test_settings = {
        "pii_salt": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "api_key_salt": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
        "gas_webhook_secret": "test-secret",
        "dashboard_admin_password": "TestPass123!",
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/15",
        "celery_broker_url": "redis://localhost:6379/14",
        "celery_result_backend": "redis://localhost:6379/13",
        "environment": "test",
        "log_level": "WARNING",
    }
    
    with patch.dict(os.environ, {k.upper(): v for k, v in test_settings.items()}):
        # Clear the lru_cache so Settings reloads with new env
        from core.config import get_settings
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
