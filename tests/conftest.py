# c:\Users\garre\OneDrive\Desktop\custom-email-api\tests\conftest.py

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# --- Add this block to fix the import path ---
# Calculate the path to the project root directory (one level up from 'tests')
project_root = Path(__file__).parent.parent
# Add the project root to the Python path
sys.path.insert(0, str(project_root))
# ---------------------------------------------

# Now the import should work because the project root is in sys.path
try:
    # Import 'app' directly from 'main.py' in the root directory
    from main import app
except ImportError as e:
    # Provide a fallback or raise a clearer error if the import fails
    raise ImportError(f"Could not import 'app' from 'main.py' in the project root "
                      f"(path added: {project_root}). "
                      f"Make sure 'main.py' exists in the root and check for other import errors. "
                      f"Original error: {e}")


@pytest.fixture(scope="function")
def client() -> TestClient:
    """
    Provides a FastAPI TestClient instance for making requests to the app.
    Scope is 'function' by default, meaning a new client is created for each test function.
    """
    # Create a TestClient instance using your FastAPI app
    test_client = TestClient(app)
    yield test_client

# --- Optional: Add other shared fixtures below ---

# Example: Fixture for database setup/teardown (more complex)
@pytest.fixture(scope="function")
def db_session():
    """
    Placeholder fixture for a database session.
    Requires implementation of TestSessionLocal and DB handling.
    """
    print("\n--- DB Session Setup (Placeholder) ---")
    session = "mock_db_session"
    try:
        yield session
    finally:
        print("\n--- DB Session Teardown (Placeholder) ---")


# Example: Fixture for mock data
@pytest.fixture
def sample_contact_payload():
    """Provides a sample dictionary representing a contact payload."""
    return {"name": "Test User", "email": "test@example.com", "phone": "1234567890"}
