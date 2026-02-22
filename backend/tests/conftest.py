"""
Pytest configuration and shared fixtures for TaskAct backend tests
"""
import pytest
import os

# Set environment variable for tests
os.environ['REACT_APP_BACKEND_URL'] = 'https://proj-manage-stage.preview.emergentagent.com'

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
