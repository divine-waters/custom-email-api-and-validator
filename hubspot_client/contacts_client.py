# hubspot_client/contacts_client.py

import os
import requests
from dotenv import load_dotenv
from utils.logger import get_logger
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
    # You might want to raise an error here or handle it depending on your app's startup requirements
    # raise ValueError("Missing HUBSPOT_API_KEY environment variable")

# Initialize the HubSpot client once
# Note: The default client is synchronous.
try:
    hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
    logger.info("✅ HubSpot client initialized successfully.")
except Exception as e:
    logger.critical(f"❌ Failed to initialize HubSpot client: {e}")
    # Depending on requirements, you might raise an error to prevent app start
    hubspot_client = None # Ensure client is None if init fails

# Define the properties we expect to exist/create
VALIDATION_PROPERTIES = {
    "email_valid_mx": {"label": "Email MX Valid", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_is_disposable": {"label": "Email Is Disposable", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_is_blacklisted": {"label": "Email Is Blacklisted", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_is_free_provider": {"label": "Email Is Free Provider", "type": "enumeration", "fieldType": "booleancheckbox", "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}]},
    "email_validation_status": {"label": "Email Validation Status", "type": "string", "fieldType": "text"},
    "email_validation_message": {"label": "Email Validation Message", "type": "string", "fieldType": "text"},
    # Add any other properties you intend to sync
}
CONTACT_PROPERTY_GROUP = "contactinformation" # Standard HubSpot group

def _handle_api_exception(e: Exception, context: str):
    """Helper function to translate ApiException or RequestException into custom HubSpot errors."""
    if not hubspot_client:
        # Corrected indentation (4 spaces)
        logger.critical("HubSpot client not initialized. Cannot handle API exception.")
        # Corrected indentation (4 spaces)
        raise HubSpotError(f"HubSpot client not initialized. Original context: {context}") from e

    status_code = None
    if isinstance(e, (ContactsApiException, PropertiesApiException)):
        status_code = e.status
        logger.error(f"HubSpot API Exception during {context}: Status={status_code}, Reason={getattr(e, 'reason', 'N/A')}, Body={getattr(e, 'body', 'N/A')}")
    elif isinstance(e, requests.exceptions.RequestException):
        if e.response is not None:
            status_code = e.response.status_code
            logger.error(f"HubSpot Request Exception during {context}: Status={status_code}, Response={e.response.text}", exc_info=False) # Log less verbosely for HTTP errors
        else:
            logger.error(f"HubSpot Request Exception during {context}: {e}", exc_info=False) # Network/connection error
        # Wrap generic request exceptions
        raise HubSpotError(message=f"Network or request error during {context}: {e}", original_exception=e) from e
    else:
        # Catch unexpected errors
        logger.exception(f"Unexpected error during {context}: {e}")
        raise HubSpotError(message=f"Unexpected error during {context}: {e}", original_exception=e) from e

    # Raise specific exceptions based on status code
    if status_code == 401:
        raise HubSpotAuthenticationError(original_exception=e) from e
    elif status_code == 403:
        # Often permissions related, treat similar to auth error for simplicity or create specific one
        # Corrected indentation (4 spaces)
        raise HubSpotAuthenticationError(message=f"HubSpot Forbidden (403) during {context}", status_code=status_code, original_exception=e) from e
    elif status_code == 404:
        # Corrected indentation (4 spaces)
        raise HubSpotNotFoundError(original_exception=e) from e
    elif status_code == 409:
        raise HubSpotConflictError(original_exception=e) from e
    elif status_code == 429:
        raise HubSpotRateLimitError(original_exception=e) from e
    elif status_code == 400:
        raise HubSpotBadRequestError(original_exception=e) from e
    elif status_code and status_code >= 500:
        # Corrected indentation (4 spaces)
        raise HubSpotServerError(original_exception=e) from e
    else:
        # Fallback for unhandled status codes or missing status
        # Corrected indentation (4 spaces)
        raise HubSpotError(message=f"Unhandled HubSpot error during {context} (Status: {status_code})", status_code=status_code, original_exception=e) from e


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
        # Fetch existing properties to minimize creation attempts (optional but good practice)
        # Note: This fetches ALL properties, could be slow. Consider checking individually if performance is key.
        # existing_props_response = hubspot_client.crm.properties.core_api.get_all(object_type="contacts")
        # existing_prop_names = {prop.name for prop in existing_props_response.results}
        # logger.info(f"Found {len(existing_prop_names)} existing contact properties.")

        # For simplicity here, we'll attempt creation and handle conflicts
        for name, details in VALIDATION_PROPERTIES.items():
            property_data = {
                "name": name,
                "label": details["label"],
                "description": f"Stores the '{details['label']}' aspect of email validation.",
                "groupName": CONTACT_PROPERTY_GROUP,
                "type": details["type"],
                "fieldType": details["fieldType"],
                # Add options only if they exist in details (for enumeration types)
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
            except PropertiesApiException as e:
                if e.status == 409:
                    logger.info(f"ℹ️ Property '{name}' already exists. Skipping.")
                    skipped_count += 1
                else:
                    # Re-raise other API errors using the handler
                    _handle_api_exception(e, f"creating property '{name}'")
            except Exception as e: # Catch other unexpected errors during creation
                # Corrected indentation (8 spaces)
                _handle_api_exception(e, f"creating property '{name}'")


        logger.info(f"🔧 HubSpot property check complete. Created: {created_count}, Skipped/Existing: {skipped_count}")

    except Exception as e:
        # Handle errors during the overall process (e.g., fetching existing properties if implemented)
        # This translates the error using our handler
        _handle_api_exception(e, "checking/creating properties")


def fetch_hubspot_contacts(limit=100, properties=None):
    """
    Fetches contacts from HubSpot using the official client.

    Args:
        limit (int): Max number of contacts per page.
        properties (list[str], optional): List of specific properties to retrieve.
                                         Defaults to basic properties + validation props.

    Returns:
        list[dict]: A list of contact objects (as dictionaries).

    Raises:
        HubSpotAuthenticationError, HubSpotRateLimitError, HubSpotError, etc.
    """
    if not hubspot_client:
        logger.error("❌ Cannot fetch contacts: HubSpot client not initialized.")
        raise HubSpotError("HubSpot client not initialized.")

    if properties is None:
        # Default properties + our custom ones
        properties = ["email", "firstname", "lastname"] + list(VALIDATION_PROPERTIES.keys())

    all_contacts = []
    after = None
    logger.info(f"Fetching HubSpot contacts with properties: {properties}")

    try:
        while True:
            page = hubspot_client.crm.contacts.basic_api.get_page(
                limit=limit,
                after=after,
                properties=properties,
                archived=False # Usually want active contacts
            )
            contacts_data = [contact.to_dict() for contact in page.results]
            all_contacts.extend(contacts_data)
            logger.debug(f"Fetched page with {len(contacts_data)} contacts. Total: {len(all_contacts)}")

            if page.paging and page.paging.next:
                after = page.paging.next.after
                logger.debug(f"Paging to next set of contacts (after={after})...")
            else:
                break # No more pages

        logger.info(f"✅ Successfully fetched {len(all_contacts)} contacts from HubSpot.")
        return all_contacts

    except (ContactsApiException, Exception) as e:
        _handle_api_exception(e, "fetching contacts")
        return [] # Should not be reached if _handle_api_exception raises, but as fallback


# Note: Changed from async def to def as standard client is synchronous
def update_contact_with_validation_result(contact_id: str, validation_properties: dict):
    """
    Updates a HubSpot contact with the provided validation properties.

    Args:
        contact_id (str): The ID of the HubSpot contact to update.
        validation_properties (dict): A dictionary containing the validation results
                                      (e.g., {"email_valid_mx": "True", ...}).
                                      Keys should match HubSpot property names.

    Returns:
        dict: The updated contact object data from HubSpot API.

    Raises:
        HubSpotAuthenticationError, HubSpotRateLimitError, HubSpotNotFoundError,
        HubSpotBadRequestError, HubSpotError, etc.
    """
    if not hubspot_client:
        logger.error(f"❌ Cannot update contact {contact_id}: HubSpot client not initialized.")
        raise HubSpotError("HubSpot client not initialized.")

    logger.info(f"Attempting to update HubSpot contact {contact_id} with validation results.")
    logger.debug(f"Update data for {contact_id}: {validation_properties}")

    # Ensure keys in validation_properties match expected VALIDATION_PROPERTIES
    update_data = {k: v for k, v in validation_properties.items() if k in VALIDATION_PROPERTIES}
    if len(update_data) != len(validation_properties):
        logger.warning(f"Some properties provided for update were filtered out for contact {contact_id} as they are not in VALIDATION_PROPERTIES.")
        logger.debug(f"Original update data: {validation_properties}, Filtered update data: {update_data}")

    if not update_data:
        logger.warning(f"No valid properties provided to update for contact {contact_id}. Skipping update.")
        # Return something indicating no update occurred, or raise specific error?
        # For now, let's return None, caller should handle.
        return None # Or maybe raise ValueError("No valid properties to update")

    contact_input = SimplePublicObjectInput(properties=update_data)

    try:
        api_response = hubspot_client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=contact_input
        )
        logger.info(f"✅ Successfully updated HubSpot contact {contact_id}.")
        return api_response.to_dict() # Return the updated contact data

    except (ContactsApiException, Exception) as e:
        _handle_api_exception(e, f"updating contact {contact_id}")
        # Should not be reached if _handle_api_exception raises


# Note: This function uses requests directly, could be refactored to use hubspot_client.crm.contacts.basic_api.create
# or search + update logic for a true "upsert". Sticking to original requests logic for now.
# Also changed validation_result param name to validation_properties for clarity
def create_or_update_hubspot_contact(email: str, firstname: str, lastname: str, validation_properties: dict):
    """
    Creates a HubSpot contact using the V3 API via requests.
    NOTE: This is a CREATE only using the provided code structure.
          A true upsert would require searching first.
    NOTE: Uses requests, not the official client like other functions.

    Args:
        email (str): Contact's email.
        firstname (str): Contact's first name.
        lastname (str): Contact's last name.
        validation_properties (dict): Dictionary of validation results.

    Returns:
        dict: The API response from HubSpot (likely the created contact object).

    Raises:
        HubSpotAuthenticationError, HubSpotRateLimitError, HubSpotBadRequestError,
        HubSpotConflictError, HubSpotError, etc.
    """
    if not HUBSPOT_API_KEY: # Check API key directly as requests is used
        logger.error("❌ Cannot create contact: HubSpot API Key not configured.")
        raise HubSpotAuthenticationError("HubSpot API Key not configured.")

    # Corrected indentation (4 spaces)
    url = f"https://api.hubapi.com/crm/v3/objects/contacts" # Use constant BASE_URL? No, it's defined locally.

    # Filter and prepare properties
    # Corrected indentation (4 spaces)
    contact_props = {
        "email": email,
        "firstname": firstname,
        "lastname": lastname,
    }
    # Add validation properties, ensuring keys are valid
    # Corrected indentation (4 spaces)
    valid_validation_props = {k: v for k, v in validation_properties.items() if k in VALIDATION_PROPERTIES}
    # Corrected indentation (4 spaces)
    contact_props.update(valid_validation_props)

    contact_data = {"properties": contact_props}

    logger.info(f"Attempting to create HubSpot contact for {email} via requests.")
    logger.debug(f"Create data for {email}: {contact_data}")

    try:
        response = requests.post(
            url,
            json=contact_data,
            headers={ # Use constant HEADERS? No, defined locally.
                "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=10 # Add a timeout
        )
        response.raise_for_status() # Raises HTTPError for 4xx/5xx
        created_contact = response.json()
        logger.info(f"✅ Contact {email} created successfully via requests (ID: {created_contact.get('id')}).")
        return created_contact # Return the actual created object data

    except requests.exceptions.RequestException as e:
        # Use the handler to translate the requests exception
        _handle_api_exception(e, f"creating contact {email} via requests")
        # Should not be reached if _handle_api_exception raises
