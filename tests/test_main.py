# c:\Users\garre\OneDrive\Desktop\custom-email-api\tests\test_main.py

import pytest # Import pytest for potential use of markers, etc.
from fastapi import status
from fastapi.testclient import TestClient # Good practice to import for type hinting

# Note: 'client', 'db_session', and 'sample_contact_payload' fixtures are
# automatically available because they are defined in conftest.py

def test_read_root(client: TestClient):
    """
    Test the root endpoint ('/').
    Assumes your root endpoint returns a JSON response.
    *** ADJUST THE EXPECTED JSON based on your actual root endpoint in app/main.py ***
    """
    response = client.get("/")

    # Check if the status code is 200 OK
    assert response.status_code == status.HTTP_200_OK

    # --- MODIFY this assertion based on what your GET "/" actually returns ---
    # Example: If it returns {"message": "Welcome!"}
    try:
        expected_json = {"message": "HubSend API is running!"} # Modify as needed
        assert response.json() == expected_json
    except Exception as e:
        pytest.fail(f"Failed to parse root response as JSON or assertion failed. "
                    f"Status: {response.status_code}, Response text: {response.text[:200]}... "
                    f"Error: {e}")


def test_read_docs(client: TestClient):
    """
    Test the auto-generated interactive API documentation endpoint ('/docs').
    This endpoint should return an HTML page (Swagger UI).
    """
    response = client.get("/docs")

    # Check if the status code is 200 OK
    assert response.status_code == status.HTTP_200_OK

    # Check if the response content type is HTML
    assert "text/html" in response.headers.get("content-type", "")

    # Optionally, check for some expected content in the HTML
    # (can be brittle if FastAPI/Swagger UI versions change)
    assert "<title>FastAPI - Swagger UI</title>" in response.text


# Example of using the sample_contact_payload fixture (demonstration)
# You would typically use this in a test file related to contact creation,
# e.g., tests/test_contacts.py
def test_payload_fixture(sample_contact_payload: dict):
    """
    Simple test to demonstrate using the sample_contact_payload fixture.
    """
    assert isinstance(sample_contact_payload, dict)
    assert sample_contact_payload["email"] == "test@example.com"
    assert "name" in sample_contact_payload


# Example of using the placeholder db_session fixture (demonstration)
# This will just print the setup/teardown messages for now.
def test_db_session_fixture_usage(db_session):
    """
    Demonstrates using the placeholder db_session fixture.
    """
    print(f"\n   Inside test_db_session_fixture_usage: Received session = {db_session}")
    assert db_session == "mock_db_session" # Check if we got the placeholder
