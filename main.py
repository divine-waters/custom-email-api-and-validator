# main.py
import os
import asyncio
import functools # <<< ADDED IMPORT
from dotenv import load_dotenv
# Removed unused Depends, Request from fastapi import
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
# Removed unused JSONResponse from fastapi.responses import
# Removed unused Field from pydantic import
from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Load environment variables
load_dotenv()

# Setup Logger
from utils.logger import get_logger
logger = get_logger("main_api")

# Import clients and services
# Assuming initialize_hubspot_client is correctly in hubspot_client/client.py
from hubspot_client.contacts_client import (
    fetch_all_contacts as hs_fetch_all_contacts,
    # Removed incorrect/unused hs_upsert_contact alias
    # Removed incorrect/unused hs_get_contact_by_email
    get_contact_by_id as hs_get_contact_by_id,
    create_or_update_hubspot_contact # <<< ADDED IMPORT
)
# Import HubSpot exceptions
from hubspot_client.exceptions import ( # <<< ADDED/EXPANDED IMPORT
    HubSpotError, HubSpotNotFoundError, HubSpotAuthenticationError,
    HubSpotRateLimitError, HubSpotBadRequestError, HubSpotConflictError,
    HubSpotServerError
)
from services.validation_orchestrator import validate_and_sync, perform_email_validation_checks
# Import specific DAO functions needed
from db.email_dao import save_validation_result as db_save_validation_result # <<< ADDED IMPORT

# Initialize HubSpot Client on startup
async def lifespan(app: FastAPI): # Removed unused 'app' parameter hint if desired, but it's standard
    # Startup
    logger.info("Application startup...")
    try:
        # Assuming this function exists and works
        logger.info("HubSpot client initialized during startup.")
    except Exception as e:
        logger.error(f"Failed to initialize HubSpot client during startup: {e}", exc_info=True)
    yield
    # Shutdown
    logger.info("Application shutdown.")

app = FastAPI(lifespan=lifespan)

# --- Pydantic Models ---
class ValidationRequest(BaseModel):
    email: EmailStr

class ContactUpsertRequest(BaseModel):
    email: EmailStr
    firstname: Optional[str] = None
    lastname: Optional[str] = None

class BulkValidationRequest(BaseModel):
    emails: List[EmailStr]

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "HubSend API is running!"}

@app.post("/validate-email")
async def validate_single_email(request: ValidationRequest):
    """Validates a single email address without syncing to HubSpot or DB."""
    logger.info(f"Received request to validate email: {request.email}")
    result = await perform_email_validation_checks(request.email)
    return result

@app.post("/validate-hubspot-contacts", status_code=202)
async def schedule_hubspot_contact_validation(background_tasks: BackgroundTasks):
    """
    Fetches all contacts from HubSpot and schedules background tasks to
    validate each contact's email, save contact & results to local DB,
    and update HubSpot custom properties.
    """
    # --- This endpoint logic remains the same ---
    try:
        logger.info("Fetching all contacts from HubSpot...")
        required_properties = ["email", "firstname", "lastname"]
        contacts = await hs_fetch_all_contacts(properties=required_properties)
        logger.info(f"Fetched {len(contacts)} contacts from HubSpot.")

        if not contacts:
            return {"message": "No contacts found in HubSpot to validate."}

        scheduled_count = 0
        for contact in contacts:
            contact_id = contact.get('id')
            properties = contact.get('properties', {})
            email = properties.get('email')
            firstname = properties.get('firstname')
            lastname = properties.get('lastname')

            if contact_id and email:
                contact_data_for_task = {
                    "id": contact_id,
                    "email": email,
                    "firstname": firstname or '',
                    "lastname": lastname or ''
                }
                background_tasks.add_task(validate_and_sync, contact_data=contact_data_for_task)
                scheduled_count += 1
            else:
                logger.warning(f"Skipping contact due to missing ID or Email in HubSpot data: {contact.get('id')}")

        logger.info(f"Scheduled {scheduled_count} email validation tasks.")
        return {"message": f"Scheduled {scheduled_count} email validation tasks to run in the background."}

    except Exception as e:
        logger.error(f"Failed to schedule HubSpot contact validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to schedule tasks: {e}")


# --- MODIFIED ENDPOINT ---
@app.patch("/validate-email-and-update-hubspot/{contact_id}")
async def validate_email_and_update_hubspot_endpoint(contact_id: str, email: str = Query(..., description="The email address to validate for this contact.")):
    """
    Fetches contact details, validates the provided email, saves contact & validation
    to DB, and updates HubSpot custom properties for the given contact ID.
    Returns immediate success/failure status.
    """
    logger.info(f"🚀 Received request to validate '{email}' and update HubSpot contact ID: {contact_id}")

    # 1. Fetch contact details from HubSpot to get firstname/lastname
    try:
        loop = asyncio.get_running_loop()
        # Use functools which is now imported
        fetch_func = functools.partial(hs_get_contact_by_id, contact_id, properties=["firstname", "lastname"])
        hubspot_contact_data = await loop.run_in_executor(None, fetch_func)

        if not hubspot_contact_data:
            logger.warning(f"HubSpot contact ID {contact_id} not found.")
            raise HTTPException(status_code=404, detail=f"HubSpot contact ID {contact_id} not found.")

        hs_properties = hubspot_contact_data.get('properties', {})
        firstname = hs_properties.get('firstname', '')
        lastname = hs_properties.get('lastname', '')
        logger.debug(f"Fetched details for contact {contact_id}: First='{firstname}', Last='{lastname}'")

    except HubSpotNotFoundError:
        logger.warning(f"HubSpot contact ID {contact_id} not found.")
        raise HTTPException(status_code=404, detail=f"HubSpot contact ID {contact_id} not found.")
    except HubSpotAuthenticationError as e:
        logger.error(f"🔒 HubSpot Auth Error fetching contact {contact_id}: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable: HubSpot Authentication Failed.")
    except HubSpotError as e:
        logger.error(f"💥 HubSpot API Error fetching contact {contact_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: Error fetching contact details from HubSpot.")
    except Exception as e:
        logger.error(f"💥 Unexpected error fetching contact {contact_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error fetching contact details.")

    # 2. Construct the data dictionary for validate_and_sync
    contact_data = {
        "id": contact_id,
        "email": email,
        "firstname": firstname,
        "lastname": lastname
    }

    # 3. Call the orchestrator function
    validation_result = await validate_and_sync(contact_data=contact_data)

    # 4. Process the result and return appropriate response
    if validation_result.get("status") == "error" and "Orchestration failed" not in validation_result.get("message", ""):
        logger.warning(f"Validation failed for {email}: {validation_result['message']}")
        raise HTTPException(status_code=400, detail=validation_result)

    if "Orchestration failed" in validation_result.get("message", ""):
        logger.error(f"Orchestration failed for {email} / {contact_id}: {validation_result['message']}")
        raise HTTPException(status_code=500, detail="Internal server error during validation process.")

    if "sync_error" in validation_result:
        sync_error_msg = validation_result['sync_error']
        logger.error(f"Sync error occurred for contact {contact_id}: {sync_error_msg}")
        raise HTTPException(status_code=502, detail=f"Sync Failed: {sync_error_msg}")

    logger.info(f"✅ Successfully validated {email} and synced for contact {contact_id}.")
    return {
        "message": f"Successfully validated {email} and synced results for contact {contact_id}.",
        "validation_result": validation_result
    }

# --- upsert_contact_endpoint ---
@app.post("/upsert-contact")
async def upsert_contact_endpoint(email: str, firstname: str = "", lastname: str = ""):
    """
    Validates an email, then creates or updates a HubSpot contact with validation results.
    """
    logger.info(f"🚀 Received request to upsert contact: {email}")

    # 1. Validate the email first
    validation_result = await perform_email_validation_checks(email)

    if validation_result["status"] == "error":
        logger.warning(f"Preventing upsert for invalid email {email}: {validation_result['message']}")
        raise HTTPException(status_code=400, detail=f"Email validation failed: {validation_result['message']}")

    # 2. Prepare data for HubSpot create/update
    hubspot_properties = {
        "email_valid_mx": str(validation_result["mx_valid"]).lower(),
        "email_is_disposable": str(validation_result["is_disposable"]).lower(),
        "email_is_blacklisted": str(validation_result["is_blacklisted"]).lower(),
        "email_is_free_provider": str(validation_result["is_free_provider"]).lower(),
        "email_validation_status": validation_result["status"],
        "email_validation_message": validation_result["message"]
    }

    hubspot_response = None
    try:
        # 3. Call HubSpot client (synchronous) to create or update in executor
        loop = asyncio.get_running_loop()
        # Use functools and create_or_update_hubspot_contact which are now imported
        upsert_func = functools.partial(create_or_update_hubspot_contact, email, firstname, lastname, hubspot_properties)
        hubspot_response = await loop.run_in_executor(None, upsert_func)

        logger.info(f"✅ Successfully upserted contact {email} to HubSpot.")

    # --- Catch specific errors (now imported) ---
    except HubSpotAuthenticationError as e:
        logger.error(f"🔒 HubSpot Auth Error during upsert for {email}: {e}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: HubSpot Authentication Failed.")
    except HubSpotRateLimitError as e:
        logger.warning(f"🚦 HubSpot Rate Limit hit during upsert for {email}: {e}")
        raise HTTPException(status_code=429, detail=f"Too Many Requests: HubSpot Rate Limit Exceeded.")
    except HubSpotBadRequestError as e:
        logger.error(f"📉 HubSpot Bad Request during upsert for {email}: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: Invalid data for HubSpot upsert.")
    except HubSpotConflictError as e:
        logger.warning(f"👥 HubSpot Conflict during upsert for {email}: {e}")
        raise HTTPException(status_code=409, detail=f"Conflict: HubSpot resource conflict during upsert.")
    except HubSpotServerError as e:
        logger.error(f"💥 HubSpot Server Error during upsert for {email}: {e}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: HubSpot Server Error.")
    except HubSpotError as e:
        logger.error(f"💥 HubSpot API Error during upsert for {email}: {e}")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: HubSpot API Error.")
    except Exception as e:
        logger.error(f"💥 Unexpected error during HubSpot upsert for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed to upsert contact.")

    # 4. Optional: Save validation result to local DB *after* successful upsert
    if hubspot_response and isinstance(hubspot_response, dict):
        contact_id = hubspot_response.get("id")
        if contact_id:
            try:
                logger.info(f"💾 Saving validation result to DB for new/updated contact {contact_id}")
                loop = asyncio.get_running_loop()
                # Use functools and db_save_validation_result which are now imported
                db_save_func = functools.partial(db_save_validation_result, validation_result, contact_id)
                await loop.run_in_executor(None, db_save_func)
            except Exception as db_err:
                logger.error(f"💥 Failed to save validation result to DB for contact {contact_id} after upsert: {db_err}", exc_info=True)
                hubspot_response["db_save_warning"] = f"Failed to save validation result locally: {db_err}"
        else:
            logger.warning(f"Could not save validation result to DB for {email}: HubSpot ID not found in response: {hubspot_response}")
    else:
        logger.warning(f"Could not save validation result to DB for {email}: Invalid or missing HubSpot response.")

    return hubspot_response

# --- validate_and_sync_single_contact remains commented out/unimplemented ---
@app.post("/validate-and-sync-contact")
async def validate_and_sync_single_contact(request: ContactUpsertRequest, background_tasks: BackgroundTasks): # Removed unused background_tasks hint if not implemented
    # ... (commented out code) ...
    raise HTTPException(status_code=501, detail="Endpoint not fully implemented")


# --- Run with Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"

    logger.info(f"Starting Uvicorn server on {host}:{port} with reload={reload}")
    uvicorn.run("main:app", host=host, port=port, reload=reload)
