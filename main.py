# main.py

import asyncio
from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import functools # Needed for run_in_executor

# Import HubSpot client functions
from hubspot_client.contacts_client import (
    create_email_validation_property,
    fetch_hubspot_contacts,
    # update_contact_with_validation_result, # Not directly called from main anymore
    create_or_update_hubspot_contact
)
# Import custom HubSpot exceptions
from hubspot_client.exceptions import (
    HubSpotError, HubSpotAuthenticationError, HubSpotRateLimitError,
    HubSpotBadRequestError, HubSpotConflictError, HubSpotServerError
)
# Import DAO for DB operations within upsert
from db.email_dao import save_validation_result as db_save_validation_result
from utils.logger import get_logger
# Import orchestrator functions
from services.validation_orchestrator import validate_and_sync, perform_email_validation_checks

load_dotenv()
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔧 Setting up HubSpot custom properties...")
    try:
        # Run the synchronous function in a thread pool executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, create_email_validation_property)
        logger.info("✅ HubSpot custom properties setup complete.")
    # --- Catch specific setup errors ---
    except HubSpotAuthenticationError as e:
        logger.critical(f"FATAL: HubSpot Authentication failed during startup: {e}. Check API Key. Exiting.")
        raise SystemExit(f"HubSpot Authentication Error: {e}") from e
    except HubSpotRateLimitError as e:
        logger.critical(f"FATAL: HubSpot Rate Limit hit during startup: {e}. Exiting.")
        raise SystemExit(f"HubSpot Rate Limit Error: {e}") from e
    except HubSpotServerError as e:
        logger.critical(f"FATAL: HubSpot Server Error during startup: {e}. Exiting.")
        raise SystemExit(f"HubSpot Server Error: {e}") from e
    except HubSpotError as e: # Catch other specific HubSpot errors
        logger.critical(f"FATAL: HubSpot API error during startup: {e}. Exiting.")
        raise SystemExit(f"HubSpot Setup Error: {e}") from e
    except Exception as e: # Catch unexpected errors during setup
        logger.critical(f"FATAL: Unexpected error during startup: {e}. Exiting.")
        raise SystemExit(f"Unexpected Startup Error: {e}") from e
    # --- End setup error handling ---
    yield
    logger.info("👋 Shutting down API.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "API is up and running!"}

@app.get("/validate-email")
async def validate_email_endpoint(email: str = Query(...)):
    """
    Validates a single email address using custom checks.
    Does not interact with HubSpot contacts or save to DB directly.
    """
    logger.info(f"🔍 Received validation request for email: {email}")
    # Call the orchestrator without a contact_id.
    # validate_and_sync internally handles its own errors including HubSpot ones if contact_id was provided.
    # If contact_id is None, no HubSpot calls are made within validate_and_sync.
    validation_result = await validate_and_sync(email=email, contact_id=None)

    # If the validation itself failed (not sync), it might be reflected in status
    if validation_result.get("status") == "error":
        logger.warning(f"Validation failed for {email}: {validation_result.get('message')}")
        # Consider returning a different HTTP status code if validation fails?
        # raise HTTPException(status_code=400, detail=validation_result)

    return validation_result

@app.post("/validate-hubspot-contacts")
async def validate_hubspot_contacts_endpoint(background_tasks: BackgroundTasks):
    """
    Fetches HubSpot contacts and schedules background validation tasks for each.
    """
    logger.info("🚀 Received request to validate HubSpot contacts.")
    contacts = []
    try:
        # Run the synchronous fetch_hubspot_contacts in an executor
        loop = asyncio.get_running_loop()
        # Pass arguments using functools.partial if needed, e.g., for limit
        # fetch_func = functools.partial(fetch_hubspot_contacts, limit=50)
        # contacts = await loop.run_in_executor(None, fetch_func)
        contacts = await loop.run_in_executor(None, fetch_hubspot_contacts)

        if not contacts:
            logger.info("📥 No contacts found in HubSpot.")
            return {"message": "No contacts found in HubSpot to validate."}

        logger.info(f"📥 Retrieved {len(contacts)} contacts from HubSpot. Scheduling validation tasks...")

    # --- Catch specific errors from fetch_hubspot_contacts ---
    except HubSpotAuthenticationError as e:
        logger.error(f"🔒 HubSpot Auth Error fetching contacts: {e}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: HubSpot Authentication Failed.") # 503 might be better than 500
    except HubSpotRateLimitError as e:
        logger.warning(f"🚦 HubSpot Rate Limit hit fetching contacts: {e}")
        raise HTTPException(status_code=429, detail=f"Too Many Requests: HubSpot Rate Limit Exceeded.")
    except HubSpotServerError as e:
        logger.error(f"💥 HubSpot Server Error fetching contacts: {e}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: HubSpot Server Error.")
    except HubSpotError as e: # Catch other specific HubSpot errors
        logger.error(f"💥 HubSpot API Error fetching contacts: {e}")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: HubSpot API Error.") # 502 Bad Gateway
    # --- Catch other potential errors during fetch ---
    except Exception as e:
        logger.error(f"💥 Unexpected error fetching HubSpot contacts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed to fetch contacts.")

    # --- Scheduling (outside the fetch try/except) ---
    try:
        count = 0
        for contact in contacts:
            # Ensure 'properties' exists and is a dict before accessing 'email'
            properties = contact.get("properties") if isinstance(contact.get("properties"), dict) else {}
            email = properties.get("email")
            contact_id = contact.get("id")

            if email and contact_id:
                # Schedule the full validation, DB save, and HubSpot update process
                # validate_and_sync handles its internal errors, including HubSpot update errors
                background_tasks.add_task(validate_and_sync, email=email, contact_id=contact_id)
                count += 1
            else:
                logger.warning(f"Skipping contact due to missing email or ID: ID={contact.get('id', 'N/A')}, Email={email}")

        logger.info(f"✅ Scheduled {count} validation tasks.")
        return {"message": f"Scheduled {count} email validation tasks to run in the background."}

    except Exception as e:
        # This catches errors during the scheduling loop itself, not background task errors
        logger.error(f"💥 Error scheduling HubSpot contact validation tasks: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed to schedule validation tasks.")


# This endpoint provides synchronous validation and update for a single contact,
# returning immediate success or failure status, including sync errors.
# It differs from '/validate-hubspot-contacts' which schedules bulk background tasks
@app.patch("/validate-email-and-update-hubspot/{contact_id}")
async def validate_email_and_update_hubspot_endpoint(contact_id: str, email: str = Query(...)):
    """
    Validates a specific email and updates the corresponding HubSpot contact.
    Also saves the result to the local database.
    """
    logger.info(f"🚀 Received request to validate {email} and update HubSpot contact ID: {contact_id}")

    # validate_and_sync handles internal errors and adds 'sync_error' if HubSpot/DB fails
    validation_result = await validate_and_sync(email=email, contact_id=contact_id)

    # Check if the validation part itself failed (e.g., bad email format)
    if validation_result.get("status") == "error" and "Orchestration failed" not in validation_result.get("message", ""):
        logger.warning(f"Validation failed for {email}: {validation_result['message']}")
        # Return 400 Bad Request if the input email validation failed
        raise HTTPException(status_code=400, detail=validation_result)

    # Check if the orchestration (e.g., unexpected error in validate_and_sync) failed
    if "Orchestration failed" in validation_result.get("message", ""):
        logger.error(f"Orchestration failed for {email} / {contact_id}: {validation_result['message']}")
        raise HTTPException(status_code=500, detail="Internal server error during validation process.")

    # Check if there was a specific error during the sync (DB/HubSpot update) part
    if "sync_error" in validation_result:
        sync_error_msg = validation_result['sync_error']
        logger.error(f"Sync error occurred for contact {contact_id}: {sync_error_msg}")
        # Return a 502 Bad Gateway if the sync with HubSpot/DB failed
        # We could potentially check the sync_error_msg for specific HubSpot error types
        # but for simplicity, a general 502 might suffice here.
        raise HTTPException(status_code=502, detail=f"Sync Failed: {sync_error_msg}")
        # Or return 200/202 with error details in body:
        # return {
        #     "message": f"Validation completed for {email}, but failed to sync results for contact {contact_id}.",
        #     "validation_result": validation_result,
        #     "sync_error": sync_error_msg
        # }

    logger.info(f"✅ Successfully validated {email} and updated contact {contact_id}.")
    return {
        "message": f"Successfully validated {email} and updated contact {contact_id}.",
        "validation_result": validation_result
    }


@app.post("/upsert-contact")
async def upsert_contact_endpoint(email: str, firstname: str = "", lastname: str = ""):
    """
    Validates an email, then creates or updates a HubSpot contact with validation results.
    """
    logger.info(f"🚀 Received request to upsert contact: {email}")

    # 1. Validate the email first
    # perform_email_validation_checks is async and doesn't call HubSpot
    validation_result = await perform_email_validation_checks(email)

    # Optional: Prevent upsert if validation status is 'error'
    if validation_result["status"] == "error":
        logger.warning(f"Preventing upsert for invalid email {email}: {validation_result['message']}")
        raise HTTPException(status_code=400, detail=f"Email validation failed: {validation_result['message']}")

    # 2. Prepare data for HubSpot create/update
    hubspot_properties = {
        # Use keys defined in hubspot_client.VALIDATION_PROPERTIES
        "email_valid_mx": str(validation_result["mx_valid"]), # Booleans as strings for HubSpot booleancheckbox
        "email_is_disposable": str(validation_result["is_disposable"]),
        "email_is_blacklisted": str(validation_result["is_blacklisted"]),
        "email_is_free_provider": str(validation_result["is_free_provider"]),
        "email_validation_status": validation_result["status"],
        "email_validation_message": validation_result["message"]
    }

    hubspot_response = None
    try:
        # 3. Call HubSpot client (synchronous) to create or update in executor
        loop = asyncio.get_running_loop()
        upsert_func = functools.partial(create_or_update_hubspot_contact, email, firstname, lastname, hubspot_properties)
        hubspot_response = await loop.run_in_executor(None, upsert_func)

        logger.info(f"✅ Successfully upserted contact {email} to HubSpot.")

    # --- Catch specific errors from create_or_update_hubspot_contact ---
    except HubSpotAuthenticationError as e:
        logger.error(f"🔒 HubSpot Auth Error during upsert for {email}: {e}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: HubSpot Authentication Failed.")
    except HubSpotRateLimitError as e:
        logger.warning(f"🚦 HubSpot Rate Limit hit during upsert for {email}: {e}")
        raise HTTPException(status_code=429, detail=f"Too Many Requests: HubSpot Rate Limit Exceeded.")
    except HubSpotBadRequestError as e:
        logger.error(f"📉 HubSpot Bad Request during upsert for {email}: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: Invalid data for HubSpot upsert.")
    except HubSpotConflictError as e: # e.g., if trying to create an existing email without proper upsert logic
        logger.warning(f"👥 HubSpot Conflict during upsert for {email}: {e}")
        raise HTTPException(status_code=409, detail=f"Conflict: HubSpot resource conflict during upsert.")
    except HubSpotServerError as e:
        logger.error(f"💥 HubSpot Server Error during upsert for {email}: {e}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: HubSpot Server Error.")
    except HubSpotError as e: # Catch other specific HubSpot errors
        logger.error(f"💥 HubSpot API Error during upsert for {email}: {e}")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: HubSpot API Error.")
    # --- Catch other potential errors during upsert ---
    except Exception as e:
        logger.error(f"💥 Unexpected error during HubSpot upsert for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed to upsert contact.")

    # 4. Optional: Save validation result to local DB *after* successful upsert
    # Ensure hubspot_response is not None and contains an ID
    if hubspot_response and isinstance(hubspot_response, dict):
        contact_id = hubspot_response.get("id")
        if contact_id:
            try:
                logger.info(f"💾 Saving validation result to DB for new/updated contact {contact_id}")
                loop = asyncio.get_running_loop()
                # Pass the original validation_result dict, not the hubspot_properties
                db_save_func = functools.partial(db_save_validation_result, validation_result, contact_id)
                await loop.run_in_executor(None, db_save_func)
            except Exception as db_err:
                # Log DB error but don't fail the request, as HubSpot upsert succeeded
                logger.error(f"💥 Failed to save validation result to DB for contact {contact_id} after upsert: {db_err}", exc_info=True)
                # Optionally add a warning to the response
                hubspot_response["db_save_warning"] = f"Failed to save validation result locally: {db_err}"
        else:
            logger.warning(f"Could not save validation result to DB for {email}: HubSpot ID not found in response: {hubspot_response}")
    else:
        logger.warning(f"Could not save validation result to DB for {email}: Invalid or missing HubSpot response.")

    return hubspot_response # Return the response from HubSpot
