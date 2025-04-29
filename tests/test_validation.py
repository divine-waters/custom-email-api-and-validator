# c:\Users\garre\OneDrive\Desktop\custom-email-api\tests\test_validation.py

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock # Import MagicMock for sync functions

# Import specific HubSpot exceptions your endpoint might catch
from hubspot_client.exceptions import HubSpotError, HubSpotNotFoundError

# Mark all tests in this module as async using pytest-asyncio
pytestmark = pytest.mark.asyncio

# --- Tests for /validate-email ---

async def test_validate_single_email_success(client: TestClient, mocker):
    """Test successful validation of a single email."""
    # Arrange
    mock_result = {"email": "garrettglick85@gmail.com", "status": "valid", "message": "Valid"}
    # Mock the underlying validation function used by the endpoint
    mock_perform_checks = mocker.patch("main.perform_email_validation_checks", return_value=mock_result)

    # Act
    response = client.post("/validate-email", json={"email": "garrettglick85@gmail.com"})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_result
    mock_perform_checks.assert_awaited_once_with("garrettglick85@gmail.com")

async def test_validate_single_email_invalid_input_format(client: TestClient):
    """Test validation endpoint fails (422) with invalid email format."""
    # Act
    response = client.post("/validate-email", json={"email": "not-an-email"})

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_validate_single_email_validation_error(client: TestClient, mocker):
    """Test validation endpoint returns result when underlying check returns error status."""
    # Arrange
    mock_result = {"email": "bad@emailkdjfk.com", "status": "invalid", "message": "Domain not found"}
    mock_perform_checks = mocker.patch("main.perform_email_validation_checks", return_value=mock_result)

    # Act
    response = client.post("/validate-email", json={"email": "bad@emailkdjfk.com"})

    # Assert: Still 200 OK, the endpoint just returns the validation result
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_result
    mock_perform_checks.assert_awaited_once_with("bad@emailkdjfk.com")


# --- Tests for /validate-hubspot-contacts ---
"""
 async def test_schedule_hubspot_validation_success(client: TestClient, mocker):
    """Test successful scheduling of background validation tasks."""
    # Arrange
    mock_contacts = [
        {"id": "1", "properties": {"email": "one@test.com", "firstname": "F1", "lastname": "L1"}},
        {"id": "2", "properties": {"email": "two@test.com", "firstname": "F2", "lastname": "L2"}},
        # Contact missing email - should be skipped
        {"id": "3", "properties": {"firstname": "F3", "lastname": "L3"}},
    ]
    # Mock the HubSpot fetch function used in main.py
    mock_fetch = mocker.patch("main.hs_fetch_all_contacts", return_value=mock_contacts)
    # Mock the background task adder
    mock_add_task = mocker.patch("main.BackgroundTasks.add_task")

    # Act
    response = client.post("/validate-hubspot-contacts")

    # Assert
    assert response.status_code == status.HTTP_202_ACCEPTED
    # Should schedule tasks only for contacts with IDs and emails (2 in this case)
    assert response.json() == {"message": "Scheduled 2 email validation tasks to run in the background."}
    mock_fetch.assert_awaited_once()
    assert mock_add_task.call_count == 2
    # Check that the correct data was passed to the first task
    # kwargs = mock_add_task.call_args_list[0]
    call_kwargs_dict = mock_add_task.call_args_list[0] # NEW: Unpack call object
    assert call_kwargs_dict['contact_data'] == {"id": "1", "email": "one@test.com", "firstname": "F1", "lastname": "L1"}
"""

async def test_schedule_hubspot_validation_no_contacts(client: TestClient, mocker):
    """Test scheduling when HubSpot returns no contacts."""
    # Arrange
    mocker.patch("main.hs_fetch_all_contacts", return_value=[])
    mock_add_task = mocker.patch("main.BackgroundTasks.add_task")

    # Act
    response = client.post("/validate-hubspot-contacts")

    # Assert: Your endpoint returns 200 OK in this case based on main.py
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"message": "No contacts found in HubSpot to validate."}
    mock_add_task.assert_not_called()


async def test_schedule_hubspot_validation_fetch_error(client: TestClient, mocker):
    """Test scheduling fails (500) when HubSpot fetch raises an error."""
    # Arrange
    mocker.patch("main.hs_fetch_all_contacts", side_effect=HubSpotError("API connection failed"))
    mock_add_task = mocker.patch("main.BackgroundTasks.add_task")

    # Act
    response = client.post("/validate-hubspot-contacts")

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to schedule tasks" in response.json()["detail"]
    mock_add_task.assert_not_called()


# --- Tests for /validate-email-and-update-hubspot/{contact_id} ---

async def test_validate_and_update_hubspot_success(client: TestClient, mocker):
    """Test successful validation and sync for a specific contact ID."""
    # Arrange
    contact_id = "987"
    email_to_validate = "garrettglick85@gmail.com"
    mock_hs_details = {"id": contact_id, "properties": {"firstname": "Specific", "lastname": "Contact"}}
    mock_sync_result = {"status": "valid", "message": "Synced OK", "hubspot_updated": True}

    # Mock the HubSpot get function (assume sync, called via executor)
    mock_hs_get = mocker.patch("main.hs_get_contact_by_id", return_value=mock_hs_details)
    # Mock the main orchestrator function
    mock_validate_sync = mocker.patch("main.validate_and_sync", return_value=mock_sync_result)

    # Act
    response = client.patch(
        f"/validate-email-and-update-hubspot/{contact_id}",
        params={"email": email_to_validate}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == f"Successfully validated {email_to_validate} and synced results for contact {contact_id}."
    assert response.json()["validation_result"] == mock_sync_result

    mock_hs_get.assert_called_once_with(contact_id, properties=["firstname", "lastname"])
    expected_contact_data = {
        "id": contact_id,
        "email": email_to_validate,
        "firstname": "Specific",
        "lastname": "Contact"
    }
    mock_validate_sync.assert_awaited_once_with(contact_data=expected_contact_data)


async def test_validate_and_update_hubspot_contact_not_found(client: TestClient, mocker):
    """Test failure (404) when HubSpot contact ID is not found."""
    # Arrange
    contact_id = "nonexistent"
    email_to_validate = "specific@example.com"
    # Mock HubSpot get to raise NotFound
    mocker.patch("main.hs_get_contact_by_id", side_effect=HubSpotNotFoundError(f"Contact {contact_id} not found"))
    mock_validate_sync = mocker.patch("main.validate_and_sync") # Ensure not called

    # Act
    response = client.patch(
        f"/validate-email-and-update-hubspot/{contact_id}",
        params={"email": email_to_validate}
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"HubSpot contact ID {contact_id} not found" in response.json()["detail"]
    mock_validate_sync.assert_not_awaited()


async def test_validate_and_update_hubspot_validation_fails_400(client: TestClient, mocker):
    """Test failure (400) when validate_and_sync returns a validation error."""
    # Arrange
    contact_id = "111"
    email_to_validate = "bad-data@example.com"
    mock_hs_details = {"id": contact_id, "properties": {"firstname": "Bad", "lastname": "Data"}}
    mock_sync_result = {"status": "error", "message": "MX record check failed"}

    mocker.patch("main.hs_get_contact_by_id", return_value=mock_hs_details)
    mocker.patch("main.validate_and_sync", return_value=mock_sync_result)

    # Act
    response = client.patch(
        f"/validate-email-and-update-hubspot/{contact_id}",
        params={"email": email_to_validate}
    )

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == mock_sync_result # Endpoint returns the validation result as detail


async def test_validate_and_update_hubspot_orchestration_fails_500(client: TestClient, mocker):
    """Test failure (500) when validate_and_sync returns an orchestration failure."""
    # Arrange
    contact_id = "222"
    email_to_validate = "fail@example.com"
    mock_hs_details = {"id": contact_id, "properties": {"firstname": "Orch", "lastname": "Fail"}}
    mock_sync_result = {"status": "error", "message": "Orchestration failed: DB unavailable"}

    mocker.patch("main.hs_get_contact_by_id", return_value=mock_hs_details)
    mocker.patch("main.validate_and_sync", return_value=mock_sync_result)

    # Act
    response = client.patch(
        f"/validate-email-and-update-hubspot/{contact_id}",
        params={"email": email_to_validate}
    )

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Internal server error during validation process" in response.json()["detail"]


# --- Test for /validate-and-sync-contact (Not Implemented) ---

async def test_validate_and_sync_contact_not_implemented(client: TestClient):
    """Test that the unimplemented endpoint returns 501."""
    # Act
    response = client.post(
        "/validate-and-sync-contact",
        json={"email": "test@example.com", "firstname": "Test"} # Example payload
    )

    # Assert
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert "Endpoint not fully implemented" in response.json()["detail"]
