# c:\Users\garre\OneDrive\Desktop\custom-email-api\tests\test_contacts.py

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock # For mocking async functions

# Import specific HubSpot exceptions your endpoint might catch
from hubspot_client.exceptions import (
    HubSpotAuthenticationError, HubSpotRateLimitError
)

# Mark all tests in this module as async using pytest-asyncio
pytestmark = pytest.mark.asyncio

# --- Tests for /upsert-contact ---

async def test_upsert_contact_success(client: TestClient, mocker):
    """
    Test successful contact upsert when email is valid and HubSpot call succeeds.
    """
    # Arrange: Mock dependencies
    mock_validation_result = {
        "email": "test@example.com", "status": "valid", "message": "Looks good",
        "mx_valid": False, "is_disposable": False, "is_blacklisted": False,
        "is_free_provider": False
    }
    mock_hubspot_response = {"id": "12345", "properties": {"email": "test@example.com"}, "isNew": True}
    mock_db_save_result = None # Assume DB save returns None on success

    # Mock the validation check within main.py
    mocker.patch("main.perform_email_validation_checks", return_value=mock_validation_result)
    # Mock the HubSpot client function within main.py
    # Use AsyncMock if the original function called via run_in_executor is async,
    # otherwise, a regular MagicMock might suffice if the target is sync.
    # Let's assume create_or_update_hubspot_contact itself is synchronous but called via executor
    mock_hs_upsert = mocker.patch("main.create_or_update_hubspot_contact", return_value=mock_hubspot_response)
    # Mock the DB save function within main.py
    mock_db_save = mocker.patch("main.db_save_validation_result", return_value=mock_db_save_result)

    # Act: Call the endpoint
    # Note: main.py uses query parameters for this endpoint
    response = client.post(
        "/upsert-contact",
        params={"email": "test@example.com", "firstname": "Test", "lastname": "User"}
    )

    # Assert: Check status code and response body
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_hubspot_response

    # In tests/test_contacts.py, inside test_upsert_contact_success

    # Assert: Check that mocks were called correctly
    mock_hs_upsert.assert_called_once()
    # Check args passed to the HubSpot mock (adjust properties based on actual logic)

    # args = mock_hs_upsert.call_args # OLD LINE
    call_args_tuple, call_kwargs_dict = mock_hs_upsert.call_args # NEW: Unpack call object

    # Now use the unpacked tuple for positional args
    assert call_args_tuple[0] == "test@example.com"
    assert call_args_tuple[1] == "Test"
    assert call_args_tuple[2] == "User"
    # The properties dict is the 4th positional argument in your main.py call
    assert call_args_tuple[3]["email_validation_status"] == "valid" # Check one property

    mock_db_save.assert_called_once()
    # Check args passed to the DB mock
    # --- FIX START ---
    # db_args, db_kwargs = mock_db_save.call_args # OLD LINE (might be okay, but let's be consistent)
    db_call_args_tuple, call_kwargs_dict = mock_db_save.call_args # NEW: Unpack call object

    assert db_call_args_tuple[0] == mock_validation_result # Passed the validation result
    assert db_call_args_tuple[1] == "12345" # Passed the HubSpot contact ID

async def test_upsert_contact_validation_fails(client: TestClient, mocker):
    """
    Test contact upsert fails (400) when email validation returns an error.
    """
    # Arrange: Mock validation to fail
    mock_validation_result = {"email": "invalid-email", "status": "error", "message": "Invalid format"}
    mocker.patch("main.perform_email_validation_checks", return_value=mock_validation_result)
    mock_hs_upsert = mocker.patch("main.create_or_update_hubspot_contact") # Mock to ensure it's NOT called
    mock_db_save = mocker.patch("main.db_save_validation_result") # Mock to ensure it's NOT called

    # Act
    response = client.post(
        "/upsert-contact",
        params={"email": "invalid-email", "firstname": "Test", "lastname": "User"}
    )

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email validation failed" in response.json()["detail"]
    mock_hs_upsert.assert_not_called()
    mock_db_save.assert_not_called()


async def test_upsert_contact_hubspot_auth_error(client: TestClient, mocker):
    """
    Test contact upsert fails (503) when HubSpot client raises AuthenticationError.
    """
    # Arrange: Mock validation success, HubSpot auth error
    mock_validation_result = {
        "email": "test@example.com", "status": "valid", "message": "Looks good",
        "mx_valid": False, "is_disposable": False, "is_blacklisted": False,
        "is_free_provider": False
    }
    mocker.patch("main.perform_email_validation_checks", return_value=mock_validation_result)
    mocker.patch("main.create_or_update_hubspot_contact", side_effect=HubSpotAuthenticationError("Invalid API key"))
    mock_db_save = mocker.patch("main.db_save_validation_result") # Mock to ensure it's NOT called

    # Act
    response = client.post(
        "/upsert-contact",
        params={"email": "test@example.com", "firstname": "Test", "lastname": "User"}
    )

    # Assert
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "HubSpot Authentication Failed" in response.json()["detail"]
    mock_db_save.assert_not_called()

# --- Add more tests for other HubSpot errors (RateLimit, BadRequest, etc.) ---
# Example:
async def test_upsert_contact_hubspot_rate_limit(client: TestClient, mocker):
    """Test contact upsert fails (429) on HubSpot RateLimitError."""
    # Arrange
    mock_validation_result = {"email": "test@example.com", "status": "valid", "message": "Looks good", "mx_valid": True, "is_disposable": False, "is_blacklisted": False, "is_free_provider": False}
    mocker.patch("main.perform_email_validation_checks", return_value=mock_validation_result)
    mocker.patch("main.create_or_update_hubspot_contact", side_effect=HubSpotRateLimitError("Rate limit exceeded"))
    mock_db_save = mocker.patch("main.db_save_validation_result")

    # Act
    response = client.post(
        "/upsert-contact",
        params={"email": "test@example.com", "firstname": "Test", "lastname": "User"}
    )

    # Assert
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "HubSpot Rate Limit Exceeded" in response.json()["detail"]
    mock_db_save.assert_not_called()


async def test_upsert_contact_db_save_fails_warning(client: TestClient, mocker):
    """
    Test upsert succeeds (200) but returns warning if DB save fails post-HubSpot success.
    """
    # Arrange
    mock_validation_result = {"email": "glickgarrett85@gmail.com", "status": "valid", "message": "Looks good", "mx_valid": True, "is_disposable": False, "is_blacklisted": False, "is_free_provider": True}
    mock_hubspot_response = {"id": "67890", "properties": {"email": "test@example.com"}, "isNew": False}
    db_error_message = "Connection timed out"

    mocker.patch("main.perform_email_validation_checks", return_value=mock_validation_result)
    mock_hs_upsert = mocker.patch("main.create_or_update_hubspot_contact", return_value=mock_hubspot_response)
    # Mock DB save to raise an exception
    mock_db_save = mocker.patch("main.db_save_validation_result", side_effect=Exception(db_error_message))

    # Act
    response = client.post(
        "/upsert-contact",
        params={"email": "test@example.com", "firstname": "Test", "lastname": "User"}
    )

    # Assert: Still 200 OK, but response includes warning
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == "67890" # HubSpot part succeeded
    assert "db_save_warning" in response_data
    assert db_error_message in response_data["db_save_warning"]

    # Assert mocks called
    mock_hs_upsert.assert_called_once()
    mock_db_save.assert_called_once()
