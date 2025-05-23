# services/validation_orchestrator.py

import asyncio
import functools
# --- MODIFIED IMPORTS ---
from db.email_dao import (
    save_validation_result as db_save_validation_result,
    upsert_contact_db as db_upsert_contact # Import the upsert function
)
# --- END MODIFIED IMPORTS ---
# Import HubSpot client function
from hubspot_client.contacts_client import update_contact_with_validation_result
# Import custom HubSpot exceptions
from hubspot_client.exceptions import (
    HubSpotError, HubSpotAuthenticationError, HubSpotRateLimitError,
    HubSpotNotFoundError, HubSpotBadRequestError, HubSpotServerError
)
from utils.logger import get_logger
from utils.domain_utils import extract_domain
from validators.mx_checker import check_mx_records
from validators.disposable_checker import is_disposable
from validators.blacklist_checker import is_blacklisted
from validators.free_provider_checker import is_free_provider

logger = get_logger("validation_orchestrator")

# perform_email_validation_checks remains the same as it doesn't call HubSpot directly
async def perform_email_validation_checks(email: str) -> dict:
    """
    Performs all individual email validation checks and returns detailed results.
    (Code remains the same as provided in the context)
    """
    if not email or '@' not in email:
        logger.warning(f"Invalid email format: {email}")
        return {
            "email": email, "domain": "", "mx_valid": False, "is_disposable": False,
            "is_blacklisted": False, "is_free_provider": False,
            "status": "error", "message": "Invalid email format."
        }

    try:
        domain = extract_domain(email)
    except ValueError as e:
        logger.error(f"Error extracting domain from {email}: {e}")
        return {
            "email": email, "domain": "", "mx_valid": False, "is_disposable": False,
            "is_blacklisted": False, "is_free_provider": False,
            "status": "error", "message": str(e)
        }

    # --- Perform Checks Concurrently ---
    mx_check_task = check_mx_records(domain)
    disposable_check_task = is_disposable(email)
    blacklist_check_task = is_blacklisted(email)
    free_provider_check_task = is_free_provider(email)

    results = await asyncio.gather(
        mx_check_task,
        disposable_check_task,
        blacklist_check_task,
        free_provider_check_task,
        return_exceptions=True # Prevent one failure from stopping others
    )

    # --- Process Results ---
    mx_records = results[0] if not isinstance(results[0], Exception) else None
    is_disposable_result = results[1] if not isinstance(results[1], Exception) else False
    is_blacklisted_result = results[2] if not isinstance(results[2], Exception) else False
    is_free_provider_result = results[3] if not isinstance(results[3], Exception) else False

    # Handle potential exceptions during checks
    if isinstance(results[0], Exception): logger.error(f"MX check failed for {domain}: {results[0]}", exc_info=False) # Log less verbosely
    if isinstance(results[1], Exception): logger.error(f"Disposable check failed for {email}: {results[1]}", exc_info=False)
    if isinstance(results[2], Exception): logger.error(f"Blacklist check failed for {email}: {results[2]}", exc_info=False)
    if isinstance(results[3], Exception): logger.error(f"Free provider check failed for {email}: {results[3]}", exc_info=False)

    mx_valid = bool(mx_records) # True if mx_records list is not empty/None

    # --- Determine Overall Status ---
    status = "valid"
    message = "Email appears valid."

    # Prioritize error conditions
    if not mx_valid:
        status = "error"
        message = "Domain has no valid MX records."
    elif is_disposable_result:
        status = "error"
        message = "Email is from a disposable provider."
    elif is_blacklisted_result:
        status = "error"
        message = "Domain is blacklisted."
    # Warning condition last
    elif is_free_provider_result:
        status = "warning"
        message = "Email is from a known free provider."

    validation_details = {
        "email": email,
        "domain": domain,
        "mx_valid": mx_valid,
        "is_disposable": is_disposable_result,
        "is_blacklisted": is_blacklisted_result,
        "is_free_provider": is_free_provider_result,
        "status": status,
        "message": message
    }

    logger.info(f"Validation result for {email}: Status='{status}', Message='{message}'")
    return validation_details

# --- MODIFIED validate_and_sync ---
async def validate_and_sync(contact_data: dict) -> dict:
    """
    Orchestrates email validation, saves contact & results to DB, and updates HubSpot.

    Args:
        contact_data (dict): A dictionary containing contact details, expected keys:
                             'id', 'email', 'firstname', 'lastname'.

    Returns:
        dict: The detailed validation result dictionary, potentially with a 'sync_error' key.
    """
    # --- Extract data - handle potential missing keys gracefully ---
    contact_id = contact_data.get('id')
    email = contact_data.get('email')
    firstname = contact_data.get('firstname', '') # Default to empty string
    lastname = contact_data.get('lastname', '')   # Default to empty string

    # --- TEMPORARY LOGGING: Check received arguments ---
    logger.debug(f"validate_and_sync received: contact_id='{contact_id}', email='{email}', firstname='{firstname}', lastname='{lastname}'")
    # --- END TEMPORARY LOGGING ---

    if not contact_id or not email:
        logger.error(f"💥 Invalid contact data received in validate_and_sync: {contact_data}")
        # Return an error structure or raise an exception
        return {
             "email": email, "status": "error",
             "message": "Missing contact ID or email for sync process."
         }

    sync_error_message = None # Initialize error message

    try:
        logger.info(f"🚀 Starting validation and sync for {email} (Contact ID: {contact_id})")

        # 1. Perform all validation checks
        validation_result = await perform_email_validation_checks(email)

        # 2. Save Contact to DB, Save Validation to DB, Update HubSpot
        loop = asyncio.get_running_loop()

        # --- Try Contact DB Upsert ---
        try:
            logger.debug(f"Attempting Contact DB upsert via executor for contact {contact_id}")
            # Use functools.partial to pass arguments to the sync function
            contact_upsert_func = functools.partial(db_upsert_contact, contact_id, firstname, lastname, email)
            await loop.run_in_executor(None, contact_upsert_func)
            logger.info(f"Contact DB upsert task completed for contact {contact_id} (check DAO logs for commit status).")
        except Exception as contact_db_err:
            logger.error(f"💥 Error during Contact DB upsert execution for contact {contact_id}: {contact_db_err}", exc_info=True)
            sync_error_message = f"Contact DB Upsert Failed: {contact_db_err}"
            # Decide if you want to stop here or continue with validation save/HubSpot update
            # For now, we'll record the error and continue

        # --- Try Validation Result DB Save ---
        try:
            logger.debug(f"Attempting Validation Result DB save via executor for contact {contact_id}")
            db_save_func = functools.partial(db_save_validation_result, validation_result, contact_id)
            await loop.run_in_executor(None, db_save_func)
            logger.info(f"Validation Result DB save task completed for contact {contact_id} (check DAO logs for commit status).")
        except Exception as db_err:
            logger.error(f"💥 Error during Validation Result DB save execution for contact {contact_id}: {db_err}", exc_info=True)
            # Append error message if one already exists from contact upsert
            sync_error_message = f"{sync_error_message}; Validation DB Save Failed: {db_err}" if sync_error_message else f"Validation DB Save Failed: {db_err}"

        # --- Try HubSpot Update ---
        try:
            logger.debug(f"Attempting HubSpot update for contact {contact_id}")
            hubspot_update_data = {
                "email_valid_mx": str(validation_result["mx_valid"]).lower(),
                "email_is_disposable": str(validation_result["is_disposable"]).lower(),
                "email_is_blacklisted": str(validation_result["is_blacklisted"]).lower(),
                "email_is_free_provider": str(validation_result["is_free_provider"]).lower(),
                "email_validation_status": validation_result["status"],
                "email_validation_message": validation_result["message"]
            }
            update_func = functools.partial(update_contact_with_validation_result, contact_id, hubspot_update_data)
            hubspot_api_response = await loop.run_in_executor(None, update_func)

            if hubspot_api_response is None:
                logger.warning(f"HubSpot update skipped for contact {contact_id} (likely no valid properties).")
            else:
                logger.info(f"🔄 HubSpot contact {contact_id} updated successfully.")

        # --- Catch Specific HubSpot Errors ---
        except HubSpotAuthenticationError as e:
            logger.error(f"🔒 HubSpot Auth Error updating contact {contact_id}: {e}")
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (Auth): {e}" if sync_error_message else f"HubSpot Update Failed (Auth): {e}"
        except HubSpotRateLimitError as e:
            logger.warning(f"🚦 HubSpot Rate Limit hit updating contact {contact_id}: {e}")
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (Rate Limit): {e}" if sync_error_message else f"HubSpot Update Failed (Rate Limit): {e}"
        except HubSpotNotFoundError as e:
            logger.warning(f"❓ HubSpot contact {contact_id} not found during update: {e}")
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (Not Found): {e}" if sync_error_message else f"HubSpot Update Failed (Not Found): {e}"
        except HubSpotBadRequestError as e:
            logger.error(f"📉 HubSpot Bad Request updating contact {contact_id}: {e}")
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (Bad Request): {e}" if sync_error_message else f"HubSpot Update Failed (Bad Request): {e}"
        except HubSpotServerError as e:
            logger.error(f"💥 HubSpot Server Error updating contact {contact_id}: {e}")
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (Server Error): {e}" if sync_error_message else f"HubSpot Update Failed (Server Error): {e}"
        except HubSpotError as e:
            logger.error(f"💥 HubSpot API Error updating contact {contact_id}: {e}")
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (API Error): {e}" if sync_error_message else f"HubSpot Update Failed (API Error): {e}"
        except Exception as hs_err:
            logger.error(f"💥 Unexpected error during HubSpot update for contact {contact_id}: {hs_err}", exc_info=True)
            sync_error_message = f"{sync_error_message}; HubSpot Update Failed (Unexpected): {hs_err}" if sync_error_message else f"HubSpot Update Failed (Unexpected): {hs_err}"
        # --- End of HubSpot update try/except ---

        # Add the sync error message to the result if one occurred
        if sync_error_message:
            validation_result["sync_error"] = sync_error_message

        # Log completion status
        completion_status = "✅ Completed" if not sync_error_message else "⚠️ Completed with errors"
        logger.info(f"{completion_status} validation and sync for {email} (Contact ID: {contact_id})")
        return validation_result

    except Exception as e:
        # Catch errors in perform_email_validation_checks or unexpected issues
        logger.error(f"💥 Unexpected error during validation orchestration for {email}: {str(e)}", exc_info=True)
        error_result = {
            "email": email, "domain": "", "mx_valid": False, "is_disposable": False,
            "is_blacklisted": False, "is_free_provider": False,
            "status": "error", "message": f"Orchestration failed: {str(e)}"
        }
        if sync_error_message: # Include sync errors if they happened before this outer exception
            error_result["sync_error"] = sync_error_message
        return error_result