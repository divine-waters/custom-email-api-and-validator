# hubspot_client/contacts_client.py

import os
import requests
import asyncio
import functools
from dotenv import load_dotenv
from utils.logger import get_logger
# --- ADDED typing imports ---
from typing import List, Optional, Dict, Any # Added Any for flexibility if needed
# --- END ADDED typing imports ---

# Import the official HubSpot client library components
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput, ApiException as ContactsApiException
from hubspot.crm.properties import ApiException as PropertiesApiException
# Import custom exceptions
from .exceptions import (
    HubSpotError, HubSpotAuthenticationError, HubSpotRateLimitError,
    HubSpotNotFoundError, HubSpotBadRequestError, HubSpotConflictError, HubSpotServerError
)

logger = get_logger("hubspot_client")
load_dotenv()

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
if not HUBSPOT_API_KEY:
    logger.critical("❌ HubSpot API Key not found in environment variables.")
    # raise ValueError("Missing HUBSPOT_API_KEY environment variable")

# Initialize the HubSpot client once
try:
    hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
    logger.info("✅ HubSpot client initialized successfully.")
except Exception as e:
    logger.critical(f"❌ Failed to initialize HubSpot client: {e}")
    hubspot_client = None

# Define the properties we expect to exist/create
VALIDATION_PROPERTIES = {
    "email_valid_mx": {"label": "Email MX Valid", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_is_disposable": {"label": "Email Is Disposable", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_is_blacklisted": {"label": "Email Is Blacklisted", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_is_free_provider": {"label": "Email Is Free Provider", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_validation_status": {"label": "Email Validation Status", "type": "string", "fieldType": "text"},
    "email_validation_message": {"label": "Email Validation Message", "type": "string", "fieldType": "text"},
}
CONTACT_PROPERTY_GROUP = "contactinformation"

# --- FIXED _handle_api_exception ---
def _handle_api_exception(e: Exception, context: str):
    """Helper function to translate ApiException or RequestException into custom HubSpot errors."""
    # Removed check for hubspot_client initialization here, assume it's checked before calling API functions

    status_code = None
    # Check specifically for the HubSpot SDK API exceptions
    if isinstance(e, (ContactsApiException, PropertiesApiException)):
        status_code = e.status
        logger.error(f"HubSpot API Exception during {context}: Status={status_code}, Reason={getattr(e, 'reason', 'N/A')}, Body={getattr(e, 'body', 'N/A')}")
    # Check for requests library exceptions (used in create_or_update_hubspot_contact)
    elif isinstance(e, requests.exceptions.RequestException):
        if e.response is not None:
            status_code = e.response.status_code
            logger.error(f"HubSpot Request Exception during {context}: Status={status_code}, Response={e.response.text}", exc_info=False)
        else:
            logger.error(f"HubSpot Request Exception during {context}: {e}", exc_info=False) # Network/connection error
        # Wrap generic request exceptions
        raise HubSpotError(message=f"Network or request error during {context}: {e}", original_exception=e) from e
    else:
        # Catch other unexpected errors
        logger.exception(f"Unexpected error during {context}: {e}") # Use logger.exception to include traceback
        raise HubSpotError(message=f"Unexpected error during {context}: {e}", original_exception=e) from e

    # Raise specific exceptions based on status code (ensure correct indentation)
    if status_code == 401:
        raise HubSpotAuthenticationError(original_exception=e) from e
    elif status_code == 403:
        raise HubSpotAuthenticationError(message=f"HubSpot Forbidden (403) during {context}", status_code=status_code, original_exception=e) from e
    elif status_code == 404:
        raise HubSpotNotFoundError(original_exception=e) from e
    elif status_code == 409:
        raise HubSpotConflictError(original_exception=e) from e
    elif status_code == 429:
        raise HubSpotRateLimitError(original_exception=e) from e
    elif status_code == 400:
        raise HubSpotBadRequestError(original_exception=e) from e
    elif status_code and status_code >= 500:
        raise HubSpotServerError(original_exception=e) from e
    else:
        # Fallback for unhandled status codes or missing status
        raise HubSpotError(message=f"Unhandled HubSpot error during {context} (Status: {status_code})", status_code=status_code, original_exception=e) from e
# --- END FIXED _handle_api_exception ---


# --- FIXED get_contact_by_id ---
def get_contact_by_id(contact_id: str, properties: Optional[List[str]] = None) -> Optional[Dict[str, Any]]: # Added type hints
    """
    Fetches a single contact by its HubSpot ID.

    Args:
        contact_id: The HubSpot contact ID.
        properties: A list of property names to retrieve.

    Returns:
        A dictionary representing the contact, or None if not found.
    """
    if not hubspot_client:
        raise HubSpotAuthenticationError("HubSpot client not initialized.")

    properties_to_fetch = properties or ["email", "firstname", "lastname"] # Default properties

    try:
        logger.debug(f"Fetching contact by ID: {contact_id} with properties: {properties_to_fetch}")
        api_response = hubspot_client.crm.contacts.basic_api.get_by_id(
            contact_id=contact_id,
            properties=properties_to_fetch,
            archived=False
        )
        logger.debug(f"HubSpot API response for get_by_id: {api_response}")
        # Convert to dict for consistent return type
        contact_data = api_response.to_dict()
        # Ensure the structure matches what might be expected (id and properties dict)
        # This might need adjustment based on how you use the result later
        return {
            "id": contact_data.get("id"),
            "properties": contact_data.get("properties", {})
        }

    # --- Corrected Exception Handling ---
    except ContactsApiException as e: # Catch the specific SDK exception
        # Call the CORRECT handler function
        _handle_api_exception(e, f"fetching contact by ID {contact_id}")
        # If _handle_api_exception raises NotFound, it won't reach here.
        # If it raises something else, it propagates.
        # If it somehow didn't raise (e.g., future logic change), handle 404 explicitly.
        if e.status == 404:
            return None # Return None specifically for 404
        # If it wasn't 404 and _handle didn't raise, something's odd, maybe raise default
        raise HubSpotError(f"Unhandled ContactsApiException state after handler for {contact_id}", original_exception=e) from e
    # --- End Corrected Exception Handling ---
    except Exception as e: # Catch other unexpected errors
        logger.error(f"Unexpected error fetching contact by ID {contact_id}: {e}", exc_info=True)
        # Use the handler for unexpected errors too
        _handle_api_exception(e, f"fetching contact by ID {contact_id}")
        # Should not be reached if handler raises, but as a safety net:
        raise HubSpotError(f"Unexpected error fetching contact by ID {contact_id}: {e}") from e
# --- END FIXED get_contact_by_id ---


# --- create_email_validation_property ---
# (Code remains the same, but ensure indentation is correct if modified)
def create_email_validation_property():
    """
    Ensures all required email validation custom properties exist in HubSpot.
    Uses the official HubSpot client library for properties.
    """
    if not hubspot_client:
        logger.error("❌ Cannot create properties: HubSpot client not initialized.")
        raise HubSpotError("HubSpot client not initialized.")

    logger.info("🔧 Checking/Creating HubSpot email validation properties...")
    created_count = 0
    skipped_count = 0

    try:
        for name, details in VALIDATION_PROPERTIES.items():
            property_data = {
                "name": name,
                "label": details["label"],
                "description": f"Stores the '{details['label']}' aspect of email validation.",
                "groupName": CONTACT_PROPERTY_GROUP,
                "type": details["type"],
                "fieldType": details["fieldType"],
                **({"options": details["options"]} if "options" in details else {})
            }
            try:
                logger.debug(f"Attempting to create property: {name}")
                hubspot_client.crm.properties.core_api.create(
                    object_type="contacts",
                    property_create=property_data
                )
                logger.info(f"✅ Created HubSpot property: {name}")
                created_count += 1
            except PropertiesApiException as e: # Catch specific exception
                if e.status == 409:
                    logger.info(f"ℹ️ Property '{name}' already exists. Skipping.")
                    skipped_count += 1
                else:
                    _handle_api_exception(e, f"creating property '{name}'")
            except Exception as e: # Catch other unexpected errors
                _handle_api_exception(e, f"creating property '{name}'") # Use handler

        logger.info(f"🔧 HubSpot property check complete. Created: {created_count}, Skipped/Existing: {skipped_count}")

    except Exception as e:
        _handle_api_exception(e, "checking/creating properties")
# --- END create_email_validation_property ---


# --- fetch_hubspot_contacts (alias fetch_all_contacts) ---
# Renamed for clarity, ensure imports in main.py are updated if needed
async def fetch_all_contacts(limit=100, properties: Optional[List[str]] = None) -> List[Dict[str, Any]]: # Added async and type hints
    """
    Fetches contacts from HubSpot using the official client. (Async wrapper)

    Args:
        limit (int): Max number of contacts per page.
        properties (list[str], optional): List of specific properties to retrieve.

    Returns:
        list[dict]: A list of contact objects (as dictionaries).
    """
    # Run the synchronous function in an executor
    loop = asyncio.get_running_loop()
    sync_func = functools.partial(_fetch_all_contacts_sync, limit=limit, properties=properties)
    return await loop.run_in_executor(None, sync_func)

def _fetch_all_contacts_sync(limit=100, properties: Optional[List[str]] = None) -> List[Dict[str, Any]]: # Sync helper
    """Synchronous implementation to fetch all contacts."""
    if not hubspot_client:
        logger.error("❌ Cannot fetch contacts: HubSpot client not initialized.")
        raise HubSpotError("HubSpot client not initialized.")

    if properties is None:
        properties = ["email", "firstname", "lastname"] + list(VALIDATION_PROPERTIES.keys())

    all_contacts_data = []
    after = None
    logger.info(f"Fetching HubSpot contacts with properties: {properties}")

    try:
        while True:
            page = hubspot_client.crm.contacts.basic_api.get_page(
                limit=limit,
                after=after,
                properties=properties,
                archived=False
            )
            # Convert results to dictionaries
            contacts_page_data = [contact.to_dict() for contact in page.results]
            # Ensure structure matches expected {"id": ..., "properties": {...}}
            formatted_page_data = [
                {"id": c.get("id"), "properties": c.get("properties", {})}
                for c in contacts_page_data
            ]
            all_contacts_data.extend(formatted_page_data)
            logger.debug(f"Fetched page with {len(formatted_page_data)} contacts. Total: {len(all_contacts_data)}")

            if page.paging and page.paging.next:
                after = page.paging.next.after
                logger.debug(f"Paging to next set of contacts (after={after})...")
            else:
                break

        logger.info(f"✅ Successfully fetched {len(all_contacts_data)} contacts from HubSpot.")
        return all_contacts_data

    except (ContactsApiException, Exception) as e:
        _handle_api_exception(e, "fetching contacts")
        return [] # Should not be reached if handler raises
# --- END fetch_hubspot_contacts ---


# --- update_contact_with_validation_result ---
# (Code remains the same, ensure indentation is correct if modified)
def update_contact_with_validation_result(contact_id: str, validation_properties: dict) -> Optional[Dict[str, Any]]: # Added return type hint
    """
    Updates a HubSpot contact with the provided validation properties.
    """
    if not hubspot_client:
        logger.error(f"❌ Cannot update contact {contact_id}: HubSpot client not initialized.")
        raise HubSpotError("HubSpot client not initialized.")

    logger.info(f"Attempting to update HubSpot contact {contact_id} with validation results.")
    logger.debug(f"Update data for {contact_id}: {validation_properties}")

    update_data = {k: v for k, v in validation_properties.items() if k in VALIDATION_PROPERTIES}
    if len(update_data) != len(validation_properties):
        logger.warning(f"Some properties provided for update were filtered out for contact {contact_id} as they are not in VALIDATION_PROPERTIES.")
        logger.debug(f"Original update data: {validation_properties}, Filtered update data: {update_data}")

    if not update_data:
        logger.warning(f"No valid properties provided to update for contact {contact_id}. Skipping update.")
        return None

    contact_input = SimplePublicObjectInput(properties=update_data)

    try:
        api_response = hubspot_client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=contact_input
        )
        logger.info(f"✅ Successfully updated HubSpot contact {contact_id}.")
        return api_response.to_dict()

    except (ContactsApiException, Exception) as e: # Catch specific and general exceptions
        _handle_api_exception(e, f"updating contact {contact_id}")
        # Should not be reached if handler raises
        return None # Add explicit return None in case handler logic changes
# --- END update_contact_with_validation_result ---


# --- create_or_update_hubspot_contact ---
# (Code remains the same, ensure indentation is correct if modified)
def create_or_update_hubspot_contact(email: str, firstname: str, lastname: str, validation_properties: dict) -> Dict[str, Any]: # Added return type hint
    """
    Creates a HubSpot contact using the V3 API via requests.
    NOTE: This is a CREATE only using the provided code structure.
    """
    if not HUBSPOT_API_KEY:
        logger.error("❌ Cannot create contact: HubSpot API Key not configured.")
        raise HubSpotAuthenticationError("HubSpot API Key not configured.")

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    contact_props = {
        "email": email,
        "firstname": firstname,
        "lastname": lastname,
    }
    valid_validation_props = {k: v for k, v in validation_properties.items() if k in VALIDATION_PROPERTIES}
    contact_props.update(valid_validation_props)
    contact_data = {"properties": contact_props}

    logger.info(f"Attempting to create HubSpot contact for {email} via requests.")
    logger.debug(f"Create data for {email}: {contact_data}")

    try:
        response = requests.post(
            url,
            json=contact_data,
            headers={
                "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        response.raise_for_status()
        created_contact = response.json()
        logger.info(f"✅ Contact {email} created successfully via requests (ID: {created_contact.get('id')}).")
        return created_contact

    except requests.exceptions.RequestException as e:
        _handle_api_exception(e, f"creating contact {email} via requests")
        # Should not be reached if handler raises
        raise HubSpotError("Failed during contact creation via requests after handling.") from e # Add fallback raise
# --- END create_or_update_hubspot_contact ---
